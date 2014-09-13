from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from . import models
from . import views


urlpatterns = [
    # TemplateView
    url(r'^template/no_template/$',
        TemplateView.as_view()),
    url(r'^template/simple/(?P<foo>\w+)/$',
        TemplateView.as_view(template_name='generic_views/about.html')),
    url(r'^template/custom/(?P<foo>\w+)/$',
        views.CustomTemplateView.as_view(template_name='generic_views/about.html')),
    url(r'^template/content_type/$',
        TemplateView.as_view(template_name='generic_views/robots.txt', content_type='text/plain')),

    url(r'^template/cached/(?P<foo>\w+)/$',
        cache_page(2.0)(TemplateView.as_view(template_name='generic_views/about.html'))),

    # DetailView
    url(r'^detail/obj/$',
        views.ObjectDetail.as_view()),
    url(r'^detail/artist/(?P<pk>[0-9]+)/$',
        views.ArtistDetail.as_view(),
        name="artist_detail"),
    url(r'^detail/author/(?P<pk>[0-9]+)/$',
        views.AuthorDetail.as_view(),
        name="author_detail"),
    url(r'^detail/author/bycustompk/(?P<foo>[0-9]+)/$',
        views.AuthorDetail.as_view(pk_url_kwarg='foo')),
    url(r'^detail/author/byslug/(?P<slug>[\w-]+)/$',
        views.AuthorDetail.as_view()),
    url(r'^detail/author/bycustomslug/(?P<foo>[\w-]+)/$',
        views.AuthorDetail.as_view(slug_url_kwarg='foo')),
    url(r'^detail/author/bypkignoreslug/(?P<pk>[0-9]+)-(?P<slug>[\w-]+)/$',
        views.AuthorDetail.as_view()),
    url(r'^detail/author/bypkandslug/(?P<pk>[0-9]+)-(?P<slug>[\w-]+)/$',
        views.AuthorDetail.as_view(query_pk_and_slug=True)),
    url(r'^detail/author/(?P<pk>[0-9]+)/template_name_suffix/$',
        views.AuthorDetail.as_view(template_name_suffix='_view')),
    url(r'^detail/author/(?P<pk>[0-9]+)/template_name/$',
        views.AuthorDetail.as_view(template_name='generic_views/about.html')),
    url(r'^detail/author/(?P<pk>[0-9]+)/context_object_name/$',
        views.AuthorDetail.as_view(context_object_name='thingy')),
    url(r'^detail/author/(?P<pk>[0-9]+)/dupe_context_object_name/$',
        views.AuthorDetail.as_view(context_object_name='object')),
    url(r'^detail/page/(?P<pk>[0-9]+)/field/$',
        views.PageDetail.as_view()),
    url(r'^detail/author/invalid/url/$',
        views.AuthorDetail.as_view()),
    url(r'^detail/author/invalid/qs/$',
        views.AuthorDetail.as_view(queryset=None)),
    url(r'^detail/nonmodel/1/$',
        views.NonModelDetail.as_view()),
    url(r'^detail/doesnotexist/(?P<pk>[0-9]+)/$',
        views.ObjectDoesNotExistDetail.as_view()),
    # FormView
    url(r'^contact/$',
        views.ContactView.as_view()),

    # Create/UpdateView
    url(r'^edit/artists/create/$',
        views.ArtistCreate.as_view()),
    url(r'^edit/artists/(?P<pk>[0-9]+)/update/$',
        views.ArtistUpdate.as_view()),

    url(r'^edit/authors/create/naive/$',
        views.NaiveAuthorCreate.as_view()),
    url(r'^edit/authors/create/redirect/$',
        views.NaiveAuthorCreate.as_view(success_url='/edit/authors/create/')),
    url(r'^edit/authors/create/interpolate_redirect/$',
        views.NaiveAuthorCreate.as_view(success_url='/edit/author/%(id)d/update/')),
    url(r'^edit/authors/create/restricted/$',
        views.AuthorCreateRestricted.as_view()),
    url(r'^edit/authors/create/$',
        views.AuthorCreate.as_view()),
    url(r'^edit/authors/create/special/$',
        views.SpecializedAuthorCreate.as_view()),

    url(r'^edit/author/(?P<pk>[0-9]+)/update/naive/$',
        views.NaiveAuthorUpdate.as_view()),
    url(r'^edit/author/(?P<pk>[0-9]+)/update/redirect/$',
        views.NaiveAuthorUpdate.as_view(success_url='/edit/authors/create/')),
    url(r'^edit/author/(?P<pk>[0-9]+)/update/interpolate_redirect/$',
        views.NaiveAuthorUpdate.as_view(success_url='/edit/author/%(id)d/update/')),
    url(r'^edit/author/(?P<pk>[0-9]+)/update/$',
        views.AuthorUpdate.as_view()),
    url(r'^edit/author/update/$',
        views.OneAuthorUpdate.as_view()),
    url(r'^edit/author/(?P<pk>[0-9]+)/update/special/$',
        views.SpecializedAuthorUpdate.as_view()),
    url(r'^edit/author/(?P<pk>[0-9]+)/delete/naive/$',
        views.NaiveAuthorDelete.as_view()),
    url(r'^edit/author/(?P<pk>[0-9]+)/delete/redirect/$',
        views.NaiveAuthorDelete.as_view(success_url='/edit/authors/create/')),
    url(r'^edit/author/(?P<pk>[0-9]+)/delete/interpolate_redirect/$',
        views.NaiveAuthorDelete.as_view(success_url='/edit/authors/create/?deleted=%(id)s')),
    url(r'^edit/author/(?P<pk>[0-9]+)/delete/$',
        views.AuthorDelete.as_view()),
    url(r'^edit/author/(?P<pk>[0-9]+)/delete/special/$',
        views.SpecializedAuthorDelete.as_view()),

    # ArchiveIndexView
    url(r'^dates/books/$',
        views.BookArchive.as_view()),
    url(r'^dates/books/context_object_name/$',
        views.BookArchive.as_view(context_object_name='thingies')),
    url(r'^dates/books/allow_empty/$',
        views.BookArchive.as_view(allow_empty=True)),
    url(r'^dates/books/template_name/$',
        views.BookArchive.as_view(template_name='generic_views/list.html')),
    url(r'^dates/books/template_name_suffix/$',
        views.BookArchive.as_view(template_name_suffix='_detail')),
    url(r'^dates/books/invalid/$',
        views.BookArchive.as_view(queryset=None)),
    url(r'^dates/books/paginated/$',
        views.BookArchive.as_view(paginate_by=10)),
    url(r'^dates/books/reverse/$',
        views.BookArchive.as_view(queryset=models.Book.objects.order_by('pubdate'))),
    url(r'^dates/books/by_month/$',
        views.BookArchive.as_view(date_list_period='month')),
    url(r'^dates/booksignings/$',
        views.BookSigningArchive.as_view()),
    url(r'^dates/books/sortedbyname/$',
        views.BookArchive.as_view(ordering='name')),
    url(r'^dates/books/sortedbynamedec/$',
        views.BookArchive.as_view(ordering='-name')),


    # ListView
    url(r'^list/dict/$',
        views.DictList.as_view()),
    url(r'^list/dict/paginated/$',
        views.DictList.as_view(paginate_by=1)),
    url(r'^list/artists/$',
        views.ArtistList.as_view(),
        name="artists_list"),
    url(r'^list/authors/$',
        views.AuthorList.as_view(),
        name="authors_list"),
    url(r'^list/authors/paginated/$',
        views.AuthorList.as_view(paginate_by=30)),
    url(r'^list/authors/paginated/(?P<page>[0-9]+)/$',
        views.AuthorList.as_view(paginate_by=30)),
    url(r'^list/authors/paginated-orphaned/$',
        views.AuthorList.as_view(paginate_by=30, paginate_orphans=2)),
    url(r'^list/authors/notempty/$',
        views.AuthorList.as_view(allow_empty=False)),
    url(r'^list/authors/notempty/paginated/$',
        views.AuthorList.as_view(allow_empty=False, paginate_by=2)),
    url(r'^list/authors/template_name/$',
        views.AuthorList.as_view(template_name='generic_views/list.html')),
    url(r'^list/authors/template_name_suffix/$',
        views.AuthorList.as_view(template_name_suffix='_objects')),
    url(r'^list/authors/context_object_name/$',
        views.AuthorList.as_view(context_object_name='author_list')),
    url(r'^list/authors/dupe_context_object_name/$',
        views.AuthorList.as_view(context_object_name='object_list')),
    url(r'^list/authors/invalid/$',
        views.AuthorList.as_view(queryset=None)),
    url(r'^list/authors/paginated/custom_class/$',
        views.AuthorList.as_view(paginate_by=5, paginator_class=views.CustomPaginator)),
    url(r'^list/authors/paginated/custom_page_kwarg/$',
        views.AuthorList.as_view(paginate_by=30, page_kwarg='pagina')),
    url(r'^list/authors/paginated/custom_constructor/$',
        views.AuthorListCustomPaginator.as_view()),
    url(r'^list/books/sorted/$',
        views.BookList.as_view(ordering='name')),
    url(r'^list/books/sortedbypagesandnamedec/$',
        views.BookList.as_view(ordering=('pages', '-name'))),

    # YearArchiveView
    # Mixing keyword and positional captures below is intentional; the views
    # ought to be able to accept either.
    url(r'^dates/books/(?P<year>[0-9]{4})/$',
        views.BookYearArchive.as_view()),
    url(r'^dates/books/(?P<year>[0-9]{4})/make_object_list/$',
        views.BookYearArchive.as_view(make_object_list=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/allow_empty/$',
        views.BookYearArchive.as_view(allow_empty=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/allow_future/$',
        views.BookYearArchive.as_view(allow_future=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/paginated/$',
        views.BookYearArchive.as_view(make_object_list=True, paginate_by=30)),
    url(r'^dates/books/(?P<year>\d{4})/sortedbyname/$',
        views.BookYearArchive.as_view(make_object_list=True, ordering='name')),
    url(r'^dates/books/(?P<year>\d{4})/sortedbypageandnamedec/$',
        views.BookYearArchive.as_view(make_object_list=True, ordering=('pages', '-name'))),
    url(r'^dates/books/no_year/$',
        views.BookYearArchive.as_view()),
    url(r'^dates/books/(?P<year>[0-9]{4})/reverse/$',
        views.BookYearArchive.as_view(queryset=models.Book.objects.order_by('pubdate'))),
    url(r'^dates/booksignings/(?P<year>[0-9]{4})/$',
        views.BookSigningYearArchive.as_view()),

    # MonthArchiveView
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/$',
        views.BookMonthArchive.as_view()),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/$',
        views.BookMonthArchive.as_view(month_format='%m')),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/allow_empty/$',
        views.BookMonthArchive.as_view(allow_empty=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/allow_future/$',
        views.BookMonthArchive.as_view(allow_future=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/paginated/$',
        views.BookMonthArchive.as_view(paginate_by=30)),
    url(r'^dates/books/(?P<year>[0-9]{4})/no_month/$',
        views.BookMonthArchive.as_view()),
    url(r'^dates/booksignings/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/$',
        views.BookSigningMonthArchive.as_view()),

    # WeekArchiveView
    url(r'^dates/books/(?P<year>[0-9]{4})/week/(?P<week>[0-9]{1,2})/$',
        views.BookWeekArchive.as_view()),
    url(r'^dates/books/(?P<year>[0-9]{4})/week/(?P<week>[0-9]{1,2})/allow_empty/$',
        views.BookWeekArchive.as_view(allow_empty=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/week/(?P<week>[0-9]{1,2})/allow_future/$',
        views.BookWeekArchive.as_view(allow_future=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/week/(?P<week>[0-9]{1,2})/paginated/$',
        views.BookWeekArchive.as_view(paginate_by=30)),
    url(r'^dates/books/(?P<year>[0-9]{4})/week/no_week/$',
        views.BookWeekArchive.as_view()),
    url(r'^dates/books/(?P<year>[0-9]{4})/week/(?P<week>[0-9]{1,2})/monday/$',
        views.BookWeekArchive.as_view(week_format='%W')),
    url(r'^dates/booksignings/(?P<year>[0-9]{4})/week/(?P<week>[0-9]{1,2})/$',
        views.BookSigningWeekArchive.as_view()),

    # DayArchiveView
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/$',
        views.BookDayArchive.as_view()),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/(?P<day>[0-9]{1,2})/$',
        views.BookDayArchive.as_view(month_format='%m')),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/allow_empty/$',
        views.BookDayArchive.as_view(allow_empty=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/allow_future/$',
        views.BookDayArchive.as_view(allow_future=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/allow_empty_and_future/$',
        views.BookDayArchive.as_view(allow_empty=True, allow_future=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/paginated/$',
        views.BookDayArchive.as_view(paginate_by=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/no_day/$',
        views.BookDayArchive.as_view()),
    url(r'^dates/booksignings/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/$',
        views.BookSigningDayArchive.as_view()),

    # TodayArchiveView
    url(r'^dates/books/today/$',
        views.BookTodayArchive.as_view()),
    url(r'^dates/books/today/allow_empty/$',
        views.BookTodayArchive.as_view(allow_empty=True)),
    url(r'^dates/booksignings/today/$',
        views.BookSigningTodayArchive.as_view()),

    # DateDetailView
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/(?P<pk>[0-9]+)/$',
        views.BookDetail.as_view()),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/(?P<day>[0-9]{1,2})/(?P<pk>[0-9]+)/$',
        views.BookDetail.as_view(month_format='%m')),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/(?P<pk>[0-9]+)/allow_future/$',
        views.BookDetail.as_view(allow_future=True)),
    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/nopk/$',
        views.BookDetail.as_view()),

    url(r'^dates/books/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/byslug/(?P<slug>[\w-]+)/$',
        views.BookDetail.as_view()),

    url(r'^dates/books/get_object_custom_queryset/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/(?P<pk>[0-9]+)/$',
        views.BookDetailGetObjectCustomQueryset.as_view()),

    url(r'^dates/booksignings/(?P<year>[0-9]{4})/(?P<month>[a-z]{3})/(?P<day>[0-9]{1,2})/(?P<pk>[0-9]+)/$',
        views.BookSigningDetail.as_view()),

    # Useful for testing redirects
    url(r'^accounts/login/$', auth_views.login)
]
