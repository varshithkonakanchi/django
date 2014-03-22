from __future__ import unicode_literals

from django.conf.urls import patterns

from .feeds import feed_dict
from .sitemaps import sitemaps


urlpatterns = patterns('',
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.gis.views.feed', {'feed_dict': feed_dict}),
)

urlpatterns += patterns('django.contrib.sitemaps.views',
    (r'^sitemaps/(?P<section>\w+)\.xml$', 'sitemap', {'sitemaps': sitemaps}),
)

urlpatterns += patterns('django.contrib.gis.sitemaps.views',
    (r'^sitemaps/kml/(?P<label>\w+)/(?P<model>\w+)/(?P<field_name>\w+)\.kml$', 'kml'),
    (r'^sitemaps/kml/(?P<label>\w+)/(?P<model>\w+)/(?P<field_name>\w+)\.kmz$', 'kmz'),
)
