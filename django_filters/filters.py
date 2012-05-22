from datetime import datetime, timedelta

from django import forms
from django.db.models import Q
from django.db.models.sql.constants import QUERY_TERMS
from django.utils.translation import ugettext_lazy as _

from django_filters.fields import RangeField, LookupTypeField

__all__ = [
    'Filter', 'CharFilter', 'BooleanFilter', 'ChoiceFilter',
    'MultipleChoiceFilter', 'DateFilter', 'DateTimeFilter', 'TimeFilter',
    'ModelChoiceFilter', 'ModelMultipleChoiceFilter', 'NumberFilter',
    'RangeFilter', 'DateRangeFilter', 'AllValuesFilter', 'RelatedObjectFilter',
]

LOOKUP_TYPES = (
    #standard Django lookups
    ('exact', _(u'Exact')), ('iexact', _(u'Exact')), ('contains', _(u'Contains')), 
    ('icontains', _(u'Contains')), ('gt', _(u'Greater than')), 
    ('gte', _(u'Greater than or equal')), ('lt', _(u'Lower than')), 
    ('lte', _(u'Lower than or equal')), ('in', _(u'Contains')),
    ('startswith', _(u'Starts with')), ('istartswith', _(u'Starts with')), 
    ('endswith', _(u'Ends with')), ('iendswith', _(u'Ends with')), 
    ('range', _(u'Range')), ('year', _(u'Year')), ('month', _(u'Month')), 
    ('day', _(u'Day')), ('week_day', _(u'Week day')), ('isnull',_(u'Is null')),
    ('search', _(u'Search')), ('regex', _(u'Regular expression')), ('iregex', _(u'Regular expression')),
    #additional lookups
    ('ex_exact', _(u'Different')), ('ex_contains', _(u'Not contains')),
    ('ex_in', _(u'Not contains')), ('ex_startswith', _(u'Not starts with')),
    ('ex_endswith', _(u'Not ends with')),
)

class Filter(object):
    creation_counter = 0
    field_class = forms.Field
    
    def __init__(self, name=None, label=None, widget=None, action=None,
        lookup_type='exact', required=False, **kwargs):
        self.name = name
        self.label = label
        if action:
            self.filter = action
        self.lookup_type = lookup_type
        self.widget = widget
        self.required = required
        self.extra = kwargs

        self.creation_counter = Filter.creation_counter
        Filter.creation_counter += 1

    @property
    def field(self):
        if not hasattr(self, '_field'):
            if self.lookup_type is None or isinstance(self.lookup_type, (list, tuple)):
                if self.lookup_type is None:
                    lookup = LOOKUP_TYPES
                else:
                    lookup = filter(lambda l: l[0] in self.lookup_type, LOOKUP_TYPES)
                self._field = LookupTypeField(self.field_class(
                    required=self.required, widget=self.widget, **self.extra),
                    lookup, required=self.required, label=self.label)
            else:
                self._field = self.field_class(required=self.required,
                    label=self.label, widget=self.widget, **self.extra)
        return self._field

    def filter(self, qs, value):
        if not value:
            return qs
        if isinstance(value, (list, tuple)):
            lookup = str(value[0])
            if not lookup:
                lookup = 'exact' # we fallback to exact if no choice for lookup is provided
            value = value[1]
        else:
            lookup = self.lookup_type
        if value:
            if not lookup.startswith('ex_'):
                return qs.filter(**{'%s__%s' % (self.name, lookup): value})
            else:
                return qs.exclude(**{'%s__%s' % (self.name, lookup.replace('ex_', '')): value})
        return qs

class CharFilter(Filter):
    field_class = forms.CharField

class BooleanFilter(Filter):
    field_class = forms.NullBooleanField

    def filter(self, qs, value):
        if value is not None:
            return qs.filter(**{self.name: value})
        return qs

class ChoiceFilter(Filter):
    field_class = forms.ChoiceField

class MultipleChoiceFilter(Filter):
    """
    This filter preforms an OR query on the selected options.
    """
    field_class = forms.MultipleChoiceField

    def filter(self, qs, value):
        value = value or ()
        lookup = 'in'
        if type(self.field) == LookupTypeField and value:
            lookup, value = value
        
        if lookup.startswith('ex_'):
            filter_type = 'exclude'
            lookup = lookup.replace('ex_', '')
        else:
            filter_type = 'filter'

        if not value:
            return qs
        
        kwargs = {'%s__%s' % (self.name, lookup): value}
        filter_method = getattr(qs, filter_type)
        return filter_method(**kwargs)

class DateFilter(Filter):
    field_class = forms.DateField

class DateTimeFilter(Filter):
    field_class = forms.DateTimeField

class TimeFilter(Filter):
    field_class = forms.TimeField

class ModelChoiceFilter(Filter):
    field_class = forms.ModelChoiceField

class ModelMultipleChoiceFilter(MultipleChoiceFilter):
    field_class = forms.ModelMultipleChoiceField

class NumberFilter(Filter):
    field_class = forms.DecimalField

class RangeFilter(Filter):
    field_class = RangeField

    def filter(self, qs, value):
        if value:
            return qs.filter(**{'%s__range' % self.name: (value.start, value.stop)})
        return qs

class DateRangeFilter(ChoiceFilter):
    options = {
        '': (_('Any Date'), lambda qs, name: qs.all()),
        1: (_('Today'), lambda qs, name: qs.filter(**{
            '%s__year' % name: datetime.today().year,
            '%s__month' % name: datetime.today().month,
            '%s__day' % name: datetime.today().day
        })),
        2: (_('Past 7 days'), lambda qs, name: qs.filter(**{
            '%s__gte' % name: (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d'),
            '%s__lt' % name: (datetime.today()+timedelta(days=1)).strftime('%Y-%m-%d'),
        })),
        3: (_('This month'), lambda qs, name: qs.filter(**{
            '%s__year' % name: datetime.today().year,
            '%s__month' % name: datetime.today().month
        })),
        4: (_('This year'), lambda qs, name: qs.filter(**{
            '%s__year' % name: datetime.today().year,
        })),
    }

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = [(key, value[0]) for key, value in self.options.iteritems()]
        super(DateRangeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = ''
        return self.options[value][1](qs, self.name)


class AllValuesFilter(ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct().order_by(self.name).values_list(self.name, flat=True)
        self.extra['choices'] = [(o, o) for o in qs]
        return super(AllValuesFilter, self).field
        
        
class RelatedObjectFilter(Filter):
    
    def __init__(self, rel_obj_field, **kwargs):
        self.rel_obj_field = rel_obj_field
        self.rel_filter = None
        super(RelatedObjectFilter, self).__init__(**kwargs)
    
    @property
    def field(self):
        if self.rel_filter is not None:
            if self.label:
                self.rel_filter.label = self.label
            return self.rel_filter.field
        return super(RelatedObjectFilter, self).field
        
    def filter(self, qs, value):
        if not value:
            return qs
        if isinstance(value, (list, tuple)):
            lookup, value = value
            if not lookup:
                lookup = 'exact' # we fallback to exact if no choice for lookup is provided
        else:
            lookup = self.lookup_type
        if value:
            if not lookup.startswith('ex_'):
                return qs.filter(**{'%s__%s' % (self.rel_obj_field, lookup): value})
            else:
                return qs.exclude(**{'%s__%s' % (self.rel_obj_field, lookup.replace('ex_', '')): value})
        return qs
    
