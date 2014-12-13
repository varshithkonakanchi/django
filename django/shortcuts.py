"""
This module collects helper functions and classes that "span" multiple levels
of MVC. In other words, these functions/classes introduce controlled coupling
for convenience's sake.
"""
import warnings

from django.template import loader, RequestContext
from django.template.context import _current_app_undefined
from django.template.engine import (
    _context_instance_undefined, _dictionary_undefined, _dirs_undefined)
from django.http import HttpResponse, Http404
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.db.models.base import ModelBase
from django.db.models.manager import Manager
from django.db.models.query import QuerySet
from django.core import urlresolvers
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning


def render_to_response(template_name, dictionary=_dictionary_undefined,
                       context_instance=_context_instance_undefined,
                       content_type=None, dirs=_dirs_undefined):
    """
    Returns a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """
    # TODO: refactor to avoid the deprecated code path.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RemovedInDjango20Warning)
        content = loader.render_to_string(template_name, dictionary, context_instance, dirs)

    return HttpResponse(content, content_type)


def render(request, template_name, dictionary=_dictionary_undefined,
           context_instance=_context_instance_undefined,
           content_type=None, status=None, current_app=_current_app_undefined,
           dirs=_dirs_undefined):
    """
    Returns a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    Uses a RequestContext by default.
    """
    if context_instance is not _context_instance_undefined:
        if current_app is not _current_app_undefined:
            raise ValueError('If you provide a context_instance you must '
                             'set its current_app before calling render()')
    else:
        context_instance = RequestContext(request, current_app=current_app)

    # TODO: refactor to avoid the deprecated code path.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RemovedInDjango20Warning)
        content = loader.render_to_string(template_name, dictionary, context_instance, dirs)

    return HttpResponse(content, content_type, status)


def redirect(to, *args, **kwargs):
    """
    Returns an HttpResponseRedirect to the appropriate URL for the arguments
    passed.

    The arguments could be:

        * A model: the model's `get_absolute_url()` function will be called.

        * A view name, possibly with arguments: `urlresolvers.reverse()` will
          be used to reverse-resolve the name.

        * A URL, which will be used as-is for the redirect location.

    By default issues a temporary redirect; pass permanent=True to issue a
    permanent redirect
    """
    if kwargs.pop('permanent', False):
        redirect_class = HttpResponsePermanentRedirect
    else:
        redirect_class = HttpResponseRedirect

    return redirect_class(resolve_url(to, *args, **kwargs))


def _get_queryset(klass):
    """
    Returns a QuerySet from a Model, Manager, or QuerySet. Created to make
    get_object_or_404 and get_list_or_404 more DRY.

    Raises a ValueError if klass is not a Model, Manager, or QuerySet.
    """
    if isinstance(klass, QuerySet):
        return klass
    elif isinstance(klass, Manager):
        manager = klass
    elif isinstance(klass, ModelBase):
        manager = klass._default_manager
    else:
        if isinstance(klass, type):
            klass__name = klass.__name__
        else:
            klass__name = klass.__class__.__name__
        raise ValueError("Object is of type '%s', but must be a Django Model, "
                         "Manager, or QuerySet" % klass__name)
    return manager.all()


def get_object_or_404(klass, *args, **kwargs):
    """
    Uses get() to return an object, or raises a Http404 exception if the object
    does not exist.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.

    Note: Like with get(), an MultipleObjectsReturned will be raised if more than one
    object is found.
    """
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        raise Http404('No %s matches the given query.' % queryset.model._meta.object_name)


def get_list_or_404(klass, *args, **kwargs):
    """
    Uses filter() to return a list of objects, or raise a Http404 exception if
    the list is empty.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the filter() query.
    """
    queryset = _get_queryset(klass)
    obj_list = list(queryset.filter(*args, **kwargs))
    if not obj_list:
        raise Http404('No %s matches the given query.' % queryset.model._meta.object_name)
    return obj_list


def resolve_url(to, *args, **kwargs):
    """
    Return a URL appropriate for the arguments passed.

    The arguments could be:

        * A model: the model's `get_absolute_url()` function will be called.

        * A view name, possibly with arguments: `urlresolvers.reverse()` will
          be used to reverse-resolve the name.

        * A URL, which will be returned as-is.

    """
    # If it's a model, use get_absolute_url()
    if hasattr(to, 'get_absolute_url'):
        return to.get_absolute_url()

    if isinstance(to, six.string_types):
        # Handle relative URLs
        if any(to.startswith(path) for path in ('./', '../')):
            return to

    # Next try a reverse URL resolution.
    try:
        return urlresolvers.reverse(to, args=args, kwargs=kwargs)
    except urlresolvers.NoReverseMatch:
        # If this is a callable, re-raise.
        if callable(to):
            raise
        # If this doesn't "feel" like a URL, re-raise.
        if '/' not in to and '.' not in to:
            raise

    # Finally, fall back and assume it's a URL
    return to
