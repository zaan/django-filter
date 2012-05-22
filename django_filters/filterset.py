from copy import deepcopy
import re
import json

from django import forms
from django.forms.forms import BoundField
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.related import RelatedObject
from django.db.models.sql.constants import LOOKUP_SEP
from django.utils.datastructures import SortedDict
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe

from django_filters.filters import Filter, CharFilter, BooleanFilter, \
    ChoiceFilter, DateFilter, DateTimeFilter, TimeFilter, ModelChoiceFilter, \
    ModelMultipleChoiceFilter, NumberFilter, RelatedObjectFilter

ORDER_BY_FIELD = 'o'
ORDER_DIRECTION_FIELD = 'sort_direction';

def get_declared_filters(bases, attrs, with_base_filters=True):
    filters = []
    for filter_name, obj in attrs.items():
        if isinstance(obj, Filter):
            obj = attrs.pop(filter_name)
            if getattr(obj, 'name', None) is None:
                obj.name = filter_name
            filters.append((filter_name, obj))
    filters.sort(key=lambda x: x[1].creation_counter)

    if with_base_filters:
        for base in bases[::-1]:
            if hasattr(base, 'base_filters'):
                filters = base.base_filters.items() + filters
    else:
        for base in bases[::-1]:
            if hasattr(base, 'declared_filters'):
                filters = base.declared_filters.items() + filters

    return SortedDict(filters)

def get_model_field(model, f):
    parts = f.split(LOOKUP_SEP)
    opts = model._meta
    for name in parts[:-1]:
        try:
            rel = opts.get_field_by_name(name)[0]
        except FieldDoesNotExist:
            return None
        if isinstance(rel, RelatedObject):
            model = rel.model
            opts = rel.opts
        else:
            model = rel.rel.to
            opts = model._meta
    try:
        rel, model, direct, m2m = opts.get_field_by_name(parts[-1])
    except FieldDoesNotExist:
        return None
    if not direct:
        return rel.field.rel.to_field
    return rel

def filters_for_model(model, fields=None, exclude=None, filter_for_field=None):
    field_dict = SortedDict()
    opts = model._meta
    if fields is None:
        fields = [f.name for f in sorted(opts.fields + opts.many_to_many)]
    for f in fields:
        if exclude is not None and f in exclude:
            continue
        field = get_model_field(model, f)
        if field is None:
            field_dict[f] = None
            continue
        filter_ = filter_for_field(field, f)
        if filter_:
            field_dict[f] = filter_
    return field_dict

def init_subfilters(cls):
    for filter_ in cls.declared_filters.values():
        if isinstance(filter_, RelatedObjectFilter):
            field = get_model_field(cls._meta.model, filter_.rel_obj_field)
            filter_.rel_filter = cls.filter_for_field(field, field.name)
            filter_.rel_filter.lookup_type = filter_.lookup_type
 
class FilterSetOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)

        self.order_by = getattr(options, 'order_by', False)

        self.form = getattr(options, 'form', forms.Form)

class FilterSetMetaclass(type):
    def __new__(cls, name, bases, attrs):
        try:
            parents = [b for b in bases if issubclass(b, FilterSet)]
        except NameError:
            # We are defining FilterSet itself here
            parents = None
        declared_filters = get_declared_filters(bases, attrs, False)
        new_class = super(FilterSetMetaclass, cls).__new__(cls, name, bases, attrs)
        if not parents:
            return new_class
        
        opts = new_class._meta = FilterSetOptions(getattr(new_class, 'Meta', None))
        if opts.model:
            filters = filters_for_model(opts.model, opts.fields, opts.exclude, new_class.filter_for_field)
            filters.update(declared_filters)
        else:
            filters = declared_filters
        if None in filters.values():
            raise TypeError("Meta.fields contains a field that isn't defined "
                "on this FilterSet")

        new_class.declared_filters = declared_filters
        new_class.base_filters = filters
        init_subfilters(new_class)
        return new_class

FILTER_FOR_DBFIELD_DEFAULTS = {
    models.CharField: {
        'filter_class': CharFilter
    },
    models.TextField: {
        'filter_class': CharFilter
    },
    models.BooleanField: {
        'filter_class': BooleanFilter
    },
    models.DateField: {
        'filter_class': DateFilter
    },
    models.DateTimeField: {
        'filter_class': DateTimeFilter
    },
    models.TimeField: {
        'filter_class': TimeFilter
    },
    models.OneToOneField: {
        'filter_class': ModelChoiceFilter,
        'extra': lambda f: {
            'queryset': f.rel.to._default_manager.complex_filter(f.rel.limit_choices_to),
            'to_field_name': f.rel.field_name,
        }
    },
    models.ForeignKey: {
        'filter_class': ModelChoiceFilter,
        'extra': lambda f: {
            'queryset': f.rel.to._default_manager.complex_filter(f.rel.limit_choices_to),
            'to_field_name': f.rel.field_name
        }
    },
    models.ManyToManyField: {
        'filter_class': ModelMultipleChoiceFilter,
        'extra': lambda f: {
            'queryset': f.rel.to._default_manager.complex_filter(f.rel.limit_choices_to),
        }
    },
    models.DecimalField: {
        'filter_class': NumberFilter,
    },
    models.SmallIntegerField: {
        'filter_class': NumberFilter,
    },
    models.IntegerField: {
        'filter_class': NumberFilter,
    },
    models.PositiveIntegerField: {
        'filter_class': NumberFilter,
    },
    models.PositiveSmallIntegerField: {
        'filter_class': NumberFilter,
    },
    models.FloatField: {
        'filter_class': NumberFilter,
    },
    models.NullBooleanField: {
        'filter_class': BooleanFilter,
    },
    models.SlugField: {
        'filter_class': CharFilter,
    },
    models.EmailField: {
        'filter_class': CharFilter,
    },
    models.FilePathField: {
        'filter_class': CharFilter,
    },
    models.URLField: {
        'filter_class': CharFilter,
    },
    models.IPAddressField: {
        'filter_class': CharFilter,
    },
    models.CommaSeparatedIntegerField: {
        'filter_class': CharFilter,
    },
}
if hasattr(models, "XMLField"):
    FILTER_FOR_DBFIELD_DEFAULTS[models.XMLField] = {
        'filter_class': CharFilter,
    }

class BaseFilterSet(object):
    filter_overrides = {}

    def __init__(self, data=None, queryset=None, prefix=None):
        self.is_bound = data is not None
        self.data = data or {}
        if queryset is None:
            queryset = self._meta.model._default_manager.all()
        self.queryset = queryset
        self.form_prefix = prefix

        self.filters = deepcopy(self.base_filters)
        # propagate the model being used through the filters
        for filter_ in self.filters.values():
            filter_.model = self._meta.model

    def __iter__(self):
        for obj in self.qs:
            yield obj

    @property
    def qs(self):
        if not hasattr(self, '_qs'):
            qs = self.queryset.all()
            for name, filter_ in self.filters.iteritems():
                try:
                    if self.is_bound:
                        data = self.form[name].data
                    else:
                        data = self.form.initial.get(name, self.form[name].field.initial)
                    val = self.form.fields[name].clean(data)
                    qs = filter_.filter(qs, val)
                except forms.ValidationError:
                    pass
            if self._meta.order_by:
                try:
                    value = self.form.fields[ORDER_BY_FIELD].clean(self.form[ORDER_BY_FIELD].data)
                    if value:
                        qs = qs.order_by(value)
                except forms.ValidationError:
                    pass
            self._qs = qs
        return self._qs

    @property
    def form(self):
        if not hasattr(self, '_form'):
            fields = SortedDict([(name, filter_.field) for name, filter_ in self.filters.iteritems()])
            fields[ORDER_BY_FIELD] = self.ordering_field
            Form =  type('%sForm' % self.__class__.__name__, (self._meta.form,), fields)
            if self.is_bound:
                self._form = Form(self.data, prefix=self.form_prefix)
            else:
                self._form = Form(prefix=self.form_prefix)
        return self._form

    def get_ordering_field(self):
        if self._meta.order_by:
            if isinstance(self._meta.order_by, (list, tuple)):
                choices = [(f, capfirst(f)) for f in self._meta.order_by]
            else:
                choices = [(f, capfirst(f)) for f in self.filters]
            return forms.ChoiceField(label="Ordering", required=False, choices=choices)

    @property
    def ordering_field(self):
        if not hasattr(self, '_ordering_field'):
            self._ordering_field = self.get_ordering_field()
        return self._ordering_field
    
    @classmethod
    def filter_for_field(cls, f, name):
        filter_for_field = dict(FILTER_FOR_DBFIELD_DEFAULTS, **cls.filter_overrides)

        default = {
            'name': name,
            'label': capfirst(f.verbose_name)
        }
        
        if f.choices:
            default['choices'] = f.choices
            return ChoiceFilter(**default)

        data = filter_for_field.get(f.__class__)
        
        if data is None:
            return
        filter_class = data.get('filter_class')
        default.update(data.get('extra', lambda f: {})(f))
        if filter_class is not None:
            return filter_class(**default)

class FilterSet(BaseFilterSet):
    __metaclass__ = FilterSetMetaclass

class DynamicFilterSet(FilterSet):
    
    def get_filters_as_options(self):
        fields = {}
        for name, filter_ in self.filters.iteritems():
            bf = BoundField(self.form, filter_.field, name)
            fields[name] = {'label': bf.label, 'label_tag': bf.label_tag(), 'widget': bf.__unicode__(), 'filter': filter_.__class__.__name__}
        return fields
        
    def get_filters_options_json(self):
        return json.dumps(self.get_filters_as_options())
    
    @property
    def dynamic_form(self):
        if not hasattr(self, '_dynamic_form'):
            filter_fields = self.get_filters_as_options()
            self.get_filters_options_json()
            FILTER_CHOICES = sorted([('', '--------')]+[(name, field['label']) for name, field in filter_fields.iteritems()], key=lambda a: a[1])
            fields = [
                ('select_field', forms.ChoiceField(choices=FILTER_CHOICES, required=False, label=_(u'Select field'))),
                #~ (ORDER_BY_FIELD, self.ordering_field),
            ]
            if self.is_bound:
                for name, filter_ in self.filters.iteritems():
                    if name in self._form_fields:
                        fields.append((name, filter_.field))
            fields = SortedDict(fields)
            Form = type('DynamicForm', (forms.Form,), fields)
            if self.is_bound:
                self._dynamic_form = Form(self.data, prefix=self.form_prefix)
                self._dynamic_form.fields.insert(0, 'select_field', self._dynamic_form.fields['select_field'])
            else:
                self._dynamic_form = Form(prefix=self.form_prefix)
        return self._dynamic_form
    
    @property
    def _form_fields(self):
        if not hasattr(self, '_ff'):
            self._ff = []
            for name in filter(lambda k: k.startswith(self.form_prefix), self.data.keys()):
                name = name.lstrip('%s-' % self.form_prefix)
                name = re.sub('_[0-9]+$', '', name)
                if name not in self._ff:
                    self._ff.append(name)
        return self._ff

class FilterSetGroup(object):
    def __init__(self, FilterSet, data, queryset=None):
        self.data = data or {}
        self.filtersets = []
        self.filterset_counter = 1
        self.queryset = queryset
        self._qs = None
        self._qsd = None
        
        if self.data:
            iter_start = self.filterset_counter
            self.filterset_counter = int(self.data.get('group-total-forms', 1))
            if self.filterset_counter is None:
                raise Exception('FilterSet counter is not included in form. Use FilterSetGroup.total_forms in your form.')
            
            for i in range(iter_start, self.filterset_counter+1):
                self.filtersets.append(FilterSet(data=self.data, prefix=str(i), queryset=self.queryset))
        else:
            self.filtersets = [FilterSet(prefix=str(self.filterset_counter), queryset=self.queryset)]
        
    def __iter__(self):
        for obj in self.qs:
            yield obj
    
    def get_fields_names(self):
        return self.filtersets[0].filters.keys()
            
    @property
    def total_forms(self):
        return mark_safe(u'<input type="hidden" name="group-total-forms" value="%s" id="id_group-total-forms" />' % self.filterset_counter)
        
    def forms(self):
        for filterset in self.filtersets:
            yield filterset.dynamic_form
    
    @property
    def base_qs(self):
        if not self._qs:
            qs = self.filtersets[0]._meta.model._default_manager.none()
            for filterset in self.filtersets:
                qs |= filterset.qs
            if self.data.get(ORDER_BY_FIELD, None):
                direction = self.data.get(ORDER_DIRECTION_FIELD, "")
                if direction != "" and direction != '-':
                    direction = ""
                orderby_field = self.data.get(ORDER_BY_FIELD)
                if orderby_field not in self.get_fields_names():
                    orderby_field = "?"
                    direction = ""
                self._qs = qs.order_by(direction + self.data.get(ORDER_BY_FIELD))
            else:
                self._qs = qs
        return self._qs
    
    @property
    def qs(self):
        if not self._qsd:
            self._qsd = self.base_qs.distinct()
        return self._qsd
        
    def get_filters_as_options(self):
        return self.filtersets[0].get_filters_options_json()
