from __future__ import absolute_import

from django.conf.urls import patterns, url
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from . import models
from . import views


urlpatterns = patterns('',
    # base
    #(r'^about/login-required/$',
    #    views.DecoratedAboutView()),

    # TemplateView
    (r'^template/no_template/$',
        TemplateView.as_view()),
    (r'^template/simple/(?P<foo>\w+)/$',
        TemplateView.as_view(template_name='generic_views/about.html')),
    (r'^template/custom/(?P<foo>\w+)/$',
        views.CustomTemplateView.as_view(template_name='generic_views/about.html')),

    (r'^template/cached/(?P<foo>\w+)/$',
        cache_page(2.0)(TemplateView.as_view(template_name='generic_views/about.html'))),

    # DetailView
    (r'^detail/obj/$',
        views.ObjectDetail.as_view()),
    url(r'^detail/artist/(?P<pk>\d+)/$',
        views.ArtistDetail.as_view(),
        name="artist_detail"),
    url(r'^detail/author/(?P<pk>\d+)/$',
        views.AuthorDetail.as_view(),
        name="author_detail"),
    (r'^detail/author/bycustompk/(?P<foo>\d+)/$',
        views.AuthorDetail.as_view(pk_url_kwarg='foo')),
    (r'^detail/author/byslug/(?P<slug>[\w-]+)/$',
        views.AuthorDetail.as_view()),
    (r'^detail/author/bycustomslug/(?P<foo>[\w-]+)/$',
        views.AuthorDetail.as_view(slug_url_kwarg='foo')),
    (r'^detail/author/(?P<pk>\d+)/template_name_suffix/$',
        views.AuthorDetail.as_view(template_name_suffix='_view')),
    (r'^detail/author/(?P<pk>\d+)/template_name/$',
        views.AuthorDetail.as_view(template_name='generic_views/about.html')),
    (r'^detail/author/(?P<pk>\d+)/context_object_name/$',
        views.AuthorDetail.as_view(context_object_name='thingy')),
    (r'^detail/author/(?P<pk>\d+)/dupe_context_object_name/$',
        views.AuthorDetail.as_view(context_object_name='object')),
    (r'^detail/page/(?P<pk>\d+)/field/$',
        views.PageDetail.as_view()),
    (r'^detail/author/invalid/url/$',
        views.AuthorDetail.as_view()),
    (r'^detail/author/invalid/qs/$',
        views.AuthorDetail.as_view(queryset=None)),
    (r'^detail/nonmodel/1/$',
        views.NonModelDetail.as_view()),

    # Create/UpdateView
    (r'^edit/artists/create/$',
        views.ArtistCreate.as_view()),
    (r'^edit/artists/(?P<pk>\d+)/update/$',
        views.ArtistUpdate.as_view()),

    (r'^edit/authors/create/naive/$',
        views.NaiveAuthorCreate.as_view()),
    (r'^edit/authors/create/redirect/$',
        views.NaiveAuthorCreate.as_view(success_url='/edit/authors/create/')),
    (r'^edit/authors/create/interpolate_redirect/$',
        views.NaiveAuthorCreate.as_view(success_url='/edit/author/%(id)d/update/')),
    (r'^edit/authors/create/restricted/$',
        views.AuthorCreateRestricted.as_view()),
    (r'^edit/authors/create/$',
        views.AuthorCreate.as_view()),
    (r'^edit/authors/create/special/$',
        views.SpecializedAuthorCreate.as_view()),

    (r'^edit/author/(?P<pk>\d+)/update/naive/$',
        views.NaiveAuthorUpdate.as_view()),
    (r'^edit/author/(?P<pk>\d+)/update/redirect/$',
        views.NaiveAuthorUpdate.as_view(success_url='/edit/authors/create/')),
    (r'^edit/author/(?P<pk>\d+)/update/interpolate_redirect/$',
        views.NaiveAuthorUpdate.as_view(success_url='/edit/author/%(id)d/update/')),
    (r'^edit/author/(?P<pk>\d+)/update/$',
        views.AuthorUpdate.as_view()),
    (r'^edit/author/update/$',
        views.OneAuthorUpdate.as_view()),
    (r'^edit/author/(?P<pk>\d+)/update/special/$',
        views.SpecializedAuthorUpdate.as_view()),
    (r'^edit/author/(?P<pk>\d+)/delete/naive/$',
        views.NaiveAuthorDelete.as_view()),
    (r'^edit/author/(?P<pk>\d+)/delete/redirect/$',
        views.NaiveAuthorDelete.as_view(success_url='/edit/authors/create/')),
    (r'^edit/author/(?P<pk>\d+)/delete/$',
        views.AuthorDelete.as_view()),
    (r'^edit/author/(?P<pk>\d+)/delete/special/$',
        views.SpecializedAuthorDelete.as_view()),

    # ArchiveIndexView
    (r'^dates/books/$',
        views.BookArchive.as_view()),
    (r'^dates/books/context_object_name/$',
        views.BookArchive.as_view(context_object_name='thingies')),
    (r'^dates/books/allow_empty/$',
        views.BookArchive.as_view(allow_empty=True)),
    (r'^dates/books/template_name/$',
        views.BookArchive.as_view(template_name='generic_views/list.html')),
    (r'^dates/books/template_name_suffix/$',
        views.BookArchive.as_view(template_name_suffix='_detail')),
    (r'^dates/books/invalid/$',
        views.BookArchive.as_view(queryset=None)),
    (r'^dates/books/paginated/$',
        views.BookArchive.as_view(paginate_by=10)),
    (r'^dates/books/reverse/$',
        views.BookArchive.as_view(queryset=models.Book.objects.order_by('pubdate'))),
    (r'^dates/books/by_month/$',
        views.BookArchive.as_view(date_list_period='month')),
    (r'^dates/booksignings/$',
        views.BookSigningArchive.as_view()),

    # ListView
    (r'^list/dict/$',
        views.DictList.as_view()),
    (r'^list/dict/paginated/$',
        views.DictList.as_view(paginate_by=1)),
    url(r'^list/artists/$',
        views.ArtistList.as_view(),
        name="artists_list"),
    url(r'^list/authors/$',
        views.AuthorList.as_view(),
        name="authors_list"),
    (r'^list/authors/paginated/$',
        views.AuthorList.as_view(paginate_by=30)),
    (r'^list/authors/paginated/(?P<page>\d+)/$',
        views.AuthorList.as_view(paginate_by=30)),
    (r'^list/authors/notempty/$',
        views.AuthorList.as_view(allow_empty=False)),
    (r'^list/authors/notempty/paginated/$',
        views.AuthorList.as_view(allow_empty=False, paginate_by=2)),
    (r'^list/authors/template_name/$',
        views.AuthorList.as_view(template_name='generic_views/list.html')),
    (r'^list/authors/template_name_suffix/$',
        views.AuthorList.as_view(template_name_suffix='_objects')),
    (r'^list/authors/context_object_name/$',
        views.AuthorList.as_view(context_object_name='author_list')),
    (r'^list/authors/dupe_context_object_name/$',
        views.AuthorList.as_view(context_object_name='object_list')),
    (r'^list/authors/invalid/$',
        views.AuthorList.as_view(queryset=None)),
    (r'^list/authors/paginated/custom_class/$',
        views.AuthorList.as_view(paginate_by=5, paginator_class=views.CustomPaginator)),
    (r'^list/authors/paginated/custom_page_kwarg/$',
        views.AuthorList.as_view(paginate_by=30, page_kwarg='pagina')),
    (r'^list/authors/paginated/custom_constructor/$',
        views.AuthorListCustomPaginator.as_view()),

    # YearArchiveView
    # Mixing keyword and possitional captures below is intentional; the views
    # ought to be able to accept either.
    (r'^dates/books/(?P<year>\d{4})/$',
        views.BookYearArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/make_object_list/$',
        views.BookYearArchive.as_view(make_object_list=True)),
    (r'^dates/books/(?P<year>\d{4})/allow_empty/$',
        views.BookYearArchive.as_view(allow_empty=True)),
    (r'^dates/books/(?P<year>\d{4})/allow_future/$',
        views.BookYearArchive.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/paginated/$',
        views.BookYearArchive.as_view(make_object_list=True, paginate_by=30)),
    (r'^dates/books/no_year/$',
        views.BookYearArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/reverse/$',
        views.BookYearArchive.as_view(queryset=models.Book.objects.order_by('pubdate'))),
    (r'^dates/booksignings/(?P<year>\d{4})/$',
        views.BookSigningYearArchive.as_view()),

    # MonthArchiveView
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/$',
        views.BookMonthArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        views.BookMonthArchive.as_view(month_format='%m')),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/allow_empty/$',
        views.BookMonthArchive.as_view(allow_empty=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/allow_future/$',
        views.BookMonthArchive.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/paginated/$',
        views.BookMonthArchive.as_view(paginate_by=30)),
    (r'^dates/books/(?P<year>\d{4})/no_month/$',
        views.BookMonthArchive.as_view()),
    (r'^dates/booksignings/(?P<year>\d{4})/(?P<month>[a-z]{3})/$',
        views.BookSigningMonthArchive.as_view()),

    # WeekArchiveView
    (r'^dates/books/(?P<year>\d{4})/week/(?P<week>\d{1,2})/$',
        views.BookWeekArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/week/(?P<week>\d{1,2})/allow_empty/$',
        views.BookWeekArchive.as_view(allow_empty=True)),
    (r'^dates/books/(?P<year>\d{4})/week/(?P<week>\d{1,2})/allow_future/$',
        views.BookWeekArchive.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/week/(?P<week>\d{1,2})/paginated/$',
        views.BookWeekArchive.as_view(paginate_by=30)),
    (r'^dates/books/(?P<year>\d{4})/week/no_week/$',
        views.BookWeekArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/week/(?P<week>\d{1,2})/monday/$',
        views.BookWeekArchive.as_view(week_format='%W')),
    (r'^dates/booksignings/(?P<year>\d{4})/week/(?P<week>\d{1,2})/$',
        views.BookSigningWeekArchive.as_view()),

    # DayArchiveView
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/$',
        views.BookDayArchive.as_view()),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        views.BookDayArchive.as_view(month_format='%m')),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/allow_empty/$',
        views.BookDayArchive.as_view(allow_empty=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/allow_future/$',
        views.BookDayArchive.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/allow_empty_and_future/$',
        views.BookDayArchive.as_view(allow_empty=True, allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/paginated/$',
        views.BookDayArchive.as_view(paginate_by=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/no_day/$',
        views.BookDayArchive.as_view()),
    (r'^dates/booksignings/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/$',
        views.BookSigningDayArchive.as_view()),

    # TodayArchiveView
    (r'^dates/books/today/$',
        views.BookTodayArchive.as_view()),
    (r'^dates/books/today/allow_empty/$',
        views.BookTodayArchive.as_view(allow_empty=True)),
    (r'^dates/booksignings/today/$',
        views.BookSigningTodayArchive.as_view()),

    # DateDetailView
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/(?P<pk>\d+)/$',
        views.BookDetail.as_view()),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<pk>\d+)/$',
        views.BookDetail.as_view(month_format='%m')),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/(?P<pk>\d+)/allow_future/$',
        views.BookDetail.as_view(allow_future=True)),
    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/nopk/$',
        views.BookDetail.as_view()),

    (r'^dates/books/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/byslug/(?P<slug>[\w-]+)/$',
        views.BookDetail.as_view()),

    (r'^dates/books/get_object_custom_queryset/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/(?P<pk>\d+)/$',
        views.BookDetailGetObjectCustomQueryset.as_view()),

    (r'^dates/booksignings/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\d{1,2})/(?P<pk>\d+)/$',
        views.BookSigningDetail.as_view()),

    # Useful for testing redirects
    (r'^accounts/login/$',  'django.contrib.auth.views.login')
)
