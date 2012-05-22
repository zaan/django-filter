
from django.shortcuts import render
from django.http import HttpResponse

from django_filters.filterset import FilterSetGroup
from sample_app.models import Person
from sample_app.filters import PersonFilterSet


def filter_persons(request):
	fitersets_group = FilterSetGroup(PersonFilterSet, request.GET or None)
	return render(request, 'sample_app/filter.html', {'fitersets_group': fitersets_group})


def test(request):
	return HttpResponse('ok')
