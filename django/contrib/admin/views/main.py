from collections import OrderedDict
import sys
import warnings

from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured
from django.core.paginator import InvalidPage
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.utils import six
from django.utils.deprecation import RenameMethodsBase
from django.utils.encoding import force_str, force_text
from django.utils.translation import ugettext, ugettext_lazy
from django.utils.http import urlencode

from django.contrib.admin import FieldListFilter
from django.contrib.admin.exceptions import DisallowedModelAdminLookup
from django.contrib.admin.options import IncorrectLookupParameters, IS_POPUP_VAR, TO_FIELD_VAR
from django.contrib.admin.utils import (quote, get_fields_from_path,
    lookup_needs_distinct, prepare_lookup_value)

# Changelist settings
ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
ERROR_FLAG = 'e'

IGNORED_PARAMS = (
    ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR, TO_FIELD_VAR)

# Text to display within change-list table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = ugettext_lazy('(None)')


def _is_changelist_popup(request):
    """
    Returns True if the popup GET parameter is set.

    This function is introduced to facilitate deprecating the legacy
    value for IS_POPUP_VAR and should be removed at the end of the
    deprecation cycle.
    """

    if IS_POPUP_VAR in request.GET:
        return True

    IS_LEGACY_POPUP_VAR = 'pop'
    if IS_LEGACY_POPUP_VAR in request.GET:
        warnings.warn(
        "The `%s` GET parameter has been renamed to `%s`." %
        (IS_LEGACY_POPUP_VAR, IS_POPUP_VAR),
        DeprecationWarning, 2)
        return True

    return False


class RenameChangeListMethods(RenameMethodsBase):
    renamed_methods = (
        ('get_query_set', 'get_queryset', DeprecationWarning),
    )


class ChangeList(six.with_metaclass(RenameChangeListMethods)):
    def __init__(self, request, model, list_display, list_display_links,
            list_filter, date_hierarchy, search_fields, list_select_related,
            list_per_page, list_max_show_all, list_editable, model_admin):
        self.model = model
        self.opts = model._meta
        self.lookup_opts = self.opts
        self.root_queryset = model_admin.get_queryset(request)
        self.list_display = list_display
        self.list_display_links = list_display_links
        self.list_filter = list_filter
        self.date_hierarchy = date_hierarchy
        self.search_fields = search_fields
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page
        self.list_max_show_all = list_max_show_all
        self.model_admin = model_admin
        self.preserved_filters = model_admin.get_preserved_filters(request)

        # Get search parameters from the query string.
        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 0))
        except ValueError:
            self.page_num = 0
        self.show_all = ALL_VAR in request.GET
        self.is_popup = _is_changelist_popup(request)
        self.to_field = request.GET.get(TO_FIELD_VAR)
        self.params = dict(request.GET.items())
        if PAGE_VAR in self.params:
            del self.params[PAGE_VAR]
        if ERROR_FLAG in self.params:
            del self.params[ERROR_FLAG]

        if self.is_popup:
            self.list_editable = ()
        else:
            self.list_editable = list_editable
        self.query = request.GET.get(SEARCH_VAR, '')
        self.queryset = self.get_queryset(request)
        self.get_results(request)
        if self.is_popup:
            title = ugettext('Select %s')
        else:
            title = ugettext('Select %s to change')
        self.title = title % force_text(self.opts.verbose_name)
        self.pk_attname = self.lookup_opts.pk.attname

    @property
    def root_query_set(self):
        warnings.warn("`ChangeList.root_query_set` is deprecated, "
                      "use `root_queryset` instead.",
                      DeprecationWarning, 2)
        return self.root_queryset

    @property
    def query_set(self):
        warnings.warn("`ChangeList.query_set` is deprecated, "
                      "use `queryset` instead.",
                      DeprecationWarning, 2)
        return self.queryset

    def get_filters_params(self, params=None):
        """
        Returns all params except IGNORED_PARAMS
        """
        if not params:
            params = self.params
        lookup_params = params.copy() # a dictionary of the query string
        # Remove all the parameters that are globally and systematically
        # ignored.
        for ignored in IGNORED_PARAMS:
            if ignored in lookup_params:
                del lookup_params[ignored]
        return lookup_params

    def get_filters(self, request):
        lookup_params = self.get_filters_params()
        use_distinct = False

        # Normalize the types of keys
        for key, value in lookup_params.items():
            if not isinstance(key, str):
                # 'key' will be used as a keyword argument later, so Python
                # requires it to be a string.
                del lookup_params[key]
                lookup_params[force_str(key)] = value

            if not self.model_admin.lookup_allowed(key, value):
                raise DisallowedModelAdminLookup("Filtering by %s not allowed" % key)

        filter_specs = []
        if self.list_filter:
            for list_filter in self.list_filter:
                if callable(list_filter):
                    # This is simply a custom list filter class.
                    spec = list_filter(request, lookup_params,
                        self.model, self.model_admin)
                else:
                    field_path = None
                    if isinstance(list_filter, (tuple, list)):
                        # This is a custom FieldListFilter class for a given field.
                        field, field_list_filter_class = list_filter
                    else:
                        # This is simply a field name, so use the default
                        # FieldListFilter class that has been registered for
                        # the type of the given field.
                        field, field_list_filter_class = list_filter, FieldListFilter.create
                    if not isinstance(field, models.Field):
                        field_path = field
                        field = get_fields_from_path(self.model, field_path)[-1]
                    spec = field_list_filter_class(field, request, lookup_params,
                        self.model, self.model_admin, field_path=field_path)
                    # Check if we need to use distinct()
                    use_distinct = (use_distinct or
                                    lookup_needs_distinct(self.lookup_opts,
                                                          field_path))
                if spec and spec.has_output():
                    filter_specs.append(spec)

        # At this point, all the parameters used by the various ListFilters
        # have been removed from lookup_params, which now only contains other
        # parameters passed via the query string. We now loop through the
        # remaining parameters both to ensure that all the parameters are valid
        # fields and to determine if at least one of them needs distinct(). If
        # the lookup parameters aren't real fields, then bail out.
        try:
            for key, value in lookup_params.items():
                lookup_params[key] = prepare_lookup_value(key, value)
                use_distinct = (use_distinct or
                                lookup_needs_distinct(self.lookup_opts, key))
            return filter_specs, bool(filter_specs), lookup_params, use_distinct
        except FieldDoesNotExist as e:
            six.reraise(IncorrectLookupParameters, IncorrectLookupParameters(e), sys.exc_info()[2])

    def get_query_string(self, new_params=None, remove=None):
        if new_params is None:
            new_params = {}
        if remove is None:
            remove = []
        p = self.params.copy()
        for r in remove:
            for k in list(p):
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v
        return '?%s' % urlencode(sorted(p.items()))

    def get_results(self, request):
        paginator = self.model_admin.get_paginator(request, self.queryset, self.list_per_page)
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count

        # Get the total number of objects, with no admin filters applied.
        # Perform a slight optimization:
        # full_result_count is equal to paginator.count if no filters
        # were applied
        if self.get_filters_params():
            full_result_count = self.root_queryset.count()
        else:
            full_result_count = result_count
        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        if (self.show_all and can_show_all) or not multi_page:
            result_list = self.queryset._clone()
        else:
            try:
                result_list = paginator.page(self.page_num+1).object_list
            except InvalidPage:
                raise IncorrectLookupParameters

        self.result_count = result_count
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator

    def _get_default_ordering(self):
        ordering = []
        if self.model_admin.ordering:
            ordering = self.model_admin.ordering
        elif self.lookup_opts.ordering:
            ordering = self.lookup_opts.ordering
        return ordering

    def get_ordering_field(self, field_name):
        """
        Returns the proper model field name corresponding to the given
        field_name to use for ordering. field_name may either be the name of a
        proper model field or the name of a method (on the admin or model) or a
        callable with the 'admin_order_field' attribute. Returns None if no
        proper model field name can be matched.
        """
        try:
            field = self.lookup_opts.get_field(field_name)
            return field.name
        except models.FieldDoesNotExist:
            # See whether field_name is a name of a non-field
            # that allows sorting.
            if callable(field_name):
                attr = field_name
            elif hasattr(self.model_admin, field_name):
                attr = getattr(self.model_admin, field_name)
            else:
                attr = getattr(self.model, field_name)
            return getattr(attr, 'admin_order_field', None)

    def get_ordering(self, request, queryset):
        """
        Returns the list of ordering fields for the change list.
        First we check the get_ordering() method in model admin, then we check
        the object's default ordering. Then, any manually-specified ordering
        from the query string overrides anything. Finally, a deterministic
        order is guaranteed by ensuring the primary key is used as the last
        ordering field.
        """
        params = self.params
        ordering = list(self.model_admin.get_ordering(request)
                        or self._get_default_ordering())
        if ORDER_VAR in params:
            # Clear ordering and used params
            ordering = []
            order_params = params[ORDER_VAR].split('.')
            for p in order_params:
                try:
                    none, pfx, idx = p.rpartition('-')
                    field_name = self.list_display[int(idx)]
                    order_field = self.get_ordering_field(field_name)
                    if not order_field:
                        continue # No 'admin_order_field', skip it
                    ordering.append(pfx + order_field)
                except (IndexError, ValueError):
                    continue # Invalid ordering specified, skip it.

        # Add the given query's ordering fields, if any.
        ordering.extend(queryset.query.order_by)

        # Ensure that the primary key is systematically present in the list of
        # ordering fields so we can guarantee a deterministic order across all
        # database backends.
        pk_name = self.lookup_opts.pk.name
        if not (set(ordering) & set(['pk', '-pk', pk_name, '-' + pk_name])):
            # The two sets do not intersect, meaning the pk isn't present. So
            # we add it.
            ordering.append('-pk')

        return ordering

    def get_ordering_field_columns(self):
        """
        Returns an OrderedDict of ordering field column numbers and asc/desc
        """

        # We must cope with more than one column having the same underlying sort
        # field, so we base things on column numbers.
        ordering = self._get_default_ordering()
        ordering_fields = OrderedDict()
        if ORDER_VAR not in self.params:
            # for ordering specified on ModelAdmin or model Meta, we don't know
            # the right column numbers absolutely, because there might be more
            # than one column associated with that ordering, so we guess.
            for field in ordering:
                if field.startswith('-'):
                    field = field[1:]
                    order_type = 'desc'
                else:
                    order_type = 'asc'
                for index, attr in enumerate(self.list_display):
                    if self.get_ordering_field(attr) == field:
                        ordering_fields[index] = order_type
                        break
        else:
            for p in self.params[ORDER_VAR].split('.'):
                none, pfx, idx = p.rpartition('-')
                try:
                    idx = int(idx)
                except ValueError:
                    continue # skip it
                ordering_fields[idx] = 'desc' if pfx == '-' else 'asc'
        return ordering_fields

    def get_queryset(self, request):
        # First, we collect all the declared list filters.
        (self.filter_specs, self.has_filters, remaining_lookup_params,
         filters_use_distinct) = self.get_filters(request)

        # Then, we let every list filter modify the queryset to its liking.
        qs = self.root_queryset
        for filter_spec in self.filter_specs:
            new_qs = filter_spec.queryset(request, qs)
            if new_qs is not None:
                qs = new_qs

        try:
            # Finally, we apply the remaining lookup parameters from the query
            # string (i.e. those that haven't already been processed by the
            # filters).
            qs = qs.filter(**remaining_lookup_params)
        except (SuspiciousOperation, ImproperlyConfigured):
            # Allow certain types of errors to be re-raised as-is so that the
            # caller can treat them in a special way.
            raise
        except Exception as e:
            # Every other error is caught with a naked except, because we don't
            # have any other way of validating lookup parameters. They might be
            # invalid if the keyword arguments are incorrect, or if the values
            # are not in the correct type, so we might get FieldError,
            # ValueError, ValidationError, or ?.
            raise IncorrectLookupParameters(e)

        if not qs.query.select_related:
            qs = self.apply_select_related(qs)

        # Set ordering.
        ordering = self.get_ordering(request, qs)
        qs = qs.order_by(*ordering)

        # Apply search results
        qs, search_use_distinct = self.model_admin.get_search_results(
            request, qs, self.query)

        # Remove duplicates from results, if necessary
        if filters_use_distinct | search_use_distinct:
            return qs.distinct()
        else:
            return qs

    def apply_select_related(self, qs):
        if self.list_select_related is True:
            return qs.select_related()

        if self.list_select_related is False:
            if self.has_related_field_in_list_display():
                return qs.select_related()

        if self.list_select_related:
            return qs.select_related(*self.list_select_related)
        return qs

    def has_related_field_in_list_display(self):
        for field_name in self.list_display:
            try:
                field = self.lookup_opts.get_field(field_name)
            except models.FieldDoesNotExist:
                pass
            else:
                if isinstance(field.rel, models.ManyToOneRel):
                    return True
        return False

    def url_for_result(self, result):
        pk = getattr(result, self.pk_attname)
        return reverse('admin:%s_%s_change' % (self.opts.app_label,
                                               self.opts.model_name),
                       args=(quote(pk),),
                       current_app=self.model_admin.admin_site.name)
