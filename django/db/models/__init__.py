from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured  # NOQA
from django.db.models.loading import (  # NOQA
    get_apps, get_app_path, get_app_paths, get_app, get_models, get_model,
    register_models, UnavailableApp)
from django.db.models.query import Q, QuerySet, Prefetch  # NOQA
from django.db.models.expressions import F  # NOQA
from django.db.models.manager import Manager  # NOQA
from django.db.models.base import Model  # NOQA
from django.db.models.aggregates import *  # NOQA
from django.db.models.fields import *  # NOQA
from django.db.models.fields.subclassing import SubfieldBase        # NOQA
from django.db.models.fields.files import FileField, ImageField  # NOQA
from django.db.models.fields.related import (  # NOQA
    ForeignKey, ForeignObject, OneToOneField, ManyToManyField,
    ManyToOneRel, ManyToManyRel, OneToOneRel)
from django.db.models.deletion import (  # NOQA
    CASCADE, PROTECT, SET, SET_NULL, SET_DEFAULT, DO_NOTHING, ProtectedError)
from django.db.models import signals  # NOQA


def permalink(func):
    """
    Decorator that calls urlresolvers.reverse() to return a URL using
    parameters returned by the decorated function "func".

    "func" should be a function that returns a tuple in one of the
    following formats:
        (viewname, viewargs)
        (viewname, viewargs, viewkwargs)
    """
    from django.core.urlresolvers import reverse

    @wraps(func)
    def inner(*args, **kwargs):
        bits = func(*args, **kwargs)
        return reverse(bits[0], None, *bits[1:3])
    return inner
