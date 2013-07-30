"""
Creates permissions for all installed apps that need permissions.
"""
from __future__ import unicode_literals

import getpass
import unicodedata

from django.contrib.auth import (models as auth_app, get_permission_codename,
    get_user_model)
from django.core import exceptions
from django.core.management.base import CommandError
from django.db import DEFAULT_DB_ALIAS, router
from django.db.models import get_model, get_models, signals, UnavailableApp
from django.utils.encoding import DEFAULT_LOCALE_ENCODING
from django.utils import six
from django.utils.six.moves import input


def _get_all_permissions(opts, ctype):
    """
    Returns (codename, name) for all permissions in the given opts.
    """
    builtin = _get_builtin_permissions(opts)
    custom = list(opts.permissions)
    _check_permission_clashing(custom, builtin, ctype)
    return builtin + custom


def _get_builtin_permissions(opts):
    """
    Returns (codename, name) for all autogenerated permissions.
    """
    perms = []
    for action in ('add', 'change', 'delete'):
        perms.append((get_permission_codename(action, opts),
            'Can %s %s' % (action, opts.verbose_name_raw)))
    return perms


def _check_permission_clashing(custom, builtin, ctype):
    """
    Check that permissions for a model do not clash. Raises CommandError if
    there are duplicate permissions.
    """
    pool = set()
    builtin_codenames = set(p[0] for p in builtin)
    for codename, _name in custom:
        if codename in pool:
            raise CommandError(
                "The permission codename '%s' is duplicated for model '%s.%s'." %
                (codename, ctype.app_label, ctype.model_class().__name__))
        elif codename in builtin_codenames:
            raise CommandError(
                "The permission codename '%s' clashes with a builtin permission "
                "for model '%s.%s'." %
                (codename, ctype.app_label, ctype.model_class().__name__))
        pool.add(codename)


def create_permissions(app, created_models, verbosity, db=DEFAULT_DB_ALIAS, **kwargs):
    try:
        get_model('auth', 'Permission')
    except UnavailableApp:
        return

    if not router.allow_syncdb(db, auth_app.Permission):
        return

    from django.contrib.contenttypes.models import ContentType

    app_models = get_models(app)

    # This will hold the permissions we're looking for as
    # (content_type, (codename, name))
    searched_perms = list()
    # The codenames and ctypes that should exist.
    ctypes = set()
    for klass in app_models:
        # Force looking up the content types in the current database
        # before creating foreign keys to them.
        ctype = ContentType.objects.db_manager(db).get_for_model(klass)
        ctypes.add(ctype)
        for perm in _get_all_permissions(klass._meta, ctype):
            searched_perms.append((ctype, perm))

    # Find all the Permissions that have a content_type for a model we're
    # looking for.  We don't need to check for codenames since we already have
    # a list of the ones we're going to create.
    all_perms = set(auth_app.Permission.objects.using(db).filter(
        content_type__in=ctypes,
    ).values_list(
        "content_type", "codename"
    ))

    perms = [
        auth_app.Permission(codename=codename, name=name, content_type=ctype)
        for ctype, (codename, name) in searched_perms
        if (ctype.pk, codename) not in all_perms
    ]
    auth_app.Permission.objects.using(db).bulk_create(perms)
    if verbosity >= 2:
        for perm in perms:
            print("Adding permission '%s'" % perm)


def create_superuser(app, created_models, verbosity, db, **kwargs):
    try:
        get_model('auth', 'Permission')
        UserModel = get_user_model()
    except UnavailableApp:
        return

    from django.core.management import call_command

    if UserModel in created_models and kwargs.get('interactive', True):
        msg = ("\nYou just installed Django's auth system, which means you "
            "don't have any superusers defined.\nWould you like to create one "
            "now? (yes/no): ")
        confirm = input(msg)
        while 1:
            if confirm not in ('yes', 'no'):
                confirm = input('Please enter either "yes" or "no": ')
                continue
            if confirm == 'yes':
                call_command("createsuperuser", interactive=True, database=db)
            break


def get_system_username():
    """
    Try to determine the current system user's username.

    :returns: The username as a unicode string, or an empty string if the
        username could not be determined.
    """
    try:
        result = getpass.getuser()
    except (ImportError, KeyError):
        # KeyError will be raised by os.getpwuid() (called by getuser())
        # if there is no corresponding entry in the /etc/passwd file
        # (a very restricted chroot environment, for example).
        return ''
    if not six.PY3:
        try:
            result = result.decode(DEFAULT_LOCALE_ENCODING)
        except UnicodeDecodeError:
            # UnicodeDecodeError - preventive treatment for non-latin Windows.
            return ''
    return result


def get_default_username(check_db=True):
    """
    Try to determine the current system user's username to use as a default.

    :param check_db: If ``True``, requires that the username does not match an
        existing ``auth.User`` (otherwise returns an empty string).
    :returns: The username, or an empty string if no username can be
        determined.
    """
    # If the User model has been swapped out, we can't make any assumptions
    # about the default user name.
    if auth_app.User._meta.swapped:
        return ''

    default_username = get_system_username()
    try:
        default_username = unicodedata.normalize('NFKD', default_username)\
            .encode('ascii', 'ignore').decode('ascii').replace(' ', '').lower()
    except UnicodeDecodeError:
        return ''

    # Run the username validator
    try:
        auth_app.User._meta.get_field('username').run_validators(default_username)
    except exceptions.ValidationError:
        return ''

    # Don't return the default username if it is already taken.
    if check_db and default_username:
        try:
            auth_app.User._default_manager.get(username=default_username)
        except auth_app.User.DoesNotExist:
            pass
        else:
            return ''
    return default_username

signals.post_migrate.connect(create_permissions,
    dispatch_uid="django.contrib.auth.management.create_permissions")
signals.post_migrate.connect(create_superuser,
    sender=auth_app, dispatch_uid="django.contrib.auth.management.create_superuser")
