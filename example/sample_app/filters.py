
import django_filters
from sample_app.models import Person, Group


class PersonFilterSet(django_filters.DynamicFilterSet):
	first_name = django_filters.CharFilter(lookup_type=('iexact', 'ex_iexact', 'istartswith', 'ex_istartswith', 'iendswith', 'ex_iendswith', 'icontains', 'ex_icontains'))
	last_name = django_filters.CharFilter(lookup_type=('iexact', 'ex_iexact', 'istartswith', 'ex_istartswith', 'iendswith', 'ex_iendswith', 'icontains', 'ex_icontains'))
	groups = django_filters.ModelMultipleChoiceFilter(queryset=Group.objects.all(), lookup_type=('in', 'ex_in'))
	group_type = django_filters.RelatedObjectFilter(rel_obj_field='groups__g_type', lookup_type=('exact', 'ex_exact'), label=u"Group type")
	
	class Meta:
		model = Person
		fields = ['first_name', 'last_name', 'sex', 'groups']
		
