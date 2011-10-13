from __future__ import absolute_import

from django.conf.urls import patterns, include

from . import views, customadmin, admin


urlpatterns = patterns('',
    (r'^test_admin/admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^test_admin/admin/secure-view/$', views.secure_view),
    (r'^test_admin/admin/', include(admin.site.urls)),
    (r'^test_admin/admin2/', include(customadmin.site.urls)),
)
