from django.conf import settings

from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'sample_app.views.filter_persons'),
)

#~ if settings.DEBUG:
    #~ urlpatterns += patterns('django.contrib.staticfiles.views',
        #~ url(r'^static/(?P<path>.*)$', 'serve'),
    #~ )
