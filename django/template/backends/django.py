# Since this package contains a "django" module, this is required on Python 2.
from __future__ import absolute_import

import sys
from importlib import import_module
from pkgutil import walk_packages

from django.apps import apps
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.context import make_context
from django.template.engine import Engine
from django.template.library import InvalidTemplateLibrary
from django.utils import six

from .base import BaseEngine


class DjangoTemplates(BaseEngine):

    app_dirname = 'templates'

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS').copy()
        options.setdefault('debug', settings.DEBUG)
        options.setdefault('file_charset', settings.FILE_CHARSET)
        libraries = options.get('libraries', {})
        options['libraries'] = self.get_templatetag_libraries(libraries)
        super(DjangoTemplates, self).__init__(params)
        self.engine = Engine(self.dirs, self.app_dirs, **options)

    def from_string(self, template_code):
        return Template(self.engine.from_string(template_code), self)

    def get_template(self, template_name):
        try:
            return Template(self.engine.get_template(template_name), self)
        except TemplateDoesNotExist as exc:
            reraise(exc, self)

    def get_templatetag_libraries(self, custom_libraries):
        """
        Return a collation of template tag libraries from installed
        applications and the supplied custom_libraries argument.
        """
        libraries = get_installed_libraries()
        libraries.update(custom_libraries)
        return libraries


class Template(object):

    def __init__(self, template, backend):
        self.template = template
        self.backend = backend

    @property
    def origin(self):
        return self.template.origin

    def render(self, context=None, request=None):
        context = make_context(context, request)
        try:
            return self.template.render(context)
        except TemplateDoesNotExist as exc:
            reraise(exc, self.backend)


def reraise(exc, backend):
    """
    Reraise TemplateDoesNotExist while maintaining template debug information.
    """
    new = exc.__class__(*exc.args, tried=exc.tried, backend=backend)
    if hasattr(exc, 'template_debug'):
        new.template_debug = exc.template_debug
    six.reraise(exc.__class__, new, sys.exc_info()[2])


def get_installed_libraries():
    """
    Return the built-in template tag libraries and those from installed
    applications. Libraries are stored in a dictionary where keys are the
    individual module names, not the full module paths. Example:
    django.templatetags.i18n is stored as i18n.
    """
    libraries = {}
    candidates = ['django.templatetags']
    candidates.extend(
        '%s.templatetags' % app_config.name
        for app_config in apps.get_app_configs())

    for candidate in candidates:
        try:
            pkg = import_module(candidate)
        except ImportError:
            # No templatetags package defined. This is safe to ignore.
            continue

        if hasattr(pkg, '__path__'):
            for name in get_package_libraries(pkg):
                libraries[name[len(candidate) + 1:]] = name

    return libraries


def get_package_libraries(pkg):
    """
    Recursively yield template tag libraries defined in submodules of a
    package.
    """
    for entry in walk_packages(pkg.__path__, pkg.__name__ + '.'):
        try:
            module = import_module(entry[1])
        except ImportError as e:
            raise InvalidTemplateLibrary(
                "Invalid template library specified. ImportError raised when "
                "trying to load '%s': %s" % (entry[1], e)
            )

        if hasattr(module, 'register'):
            yield entry[1]
