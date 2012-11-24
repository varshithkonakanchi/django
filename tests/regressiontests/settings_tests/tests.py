import os
import warnings

from django.conf import settings, global_settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.test import TransactionTestCase, TestCase, signals
from django.test.utils import override_settings
from django.utils import unittest, six


@override_settings(TEST='override')
class FullyDecoratedTranTestCase(TransactionTestCase):

    def test_override(self):
        self.assertEqual(settings.TEST, 'override')

    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertEqual(settings.TEST, 'override2')

    def test_decorated_testcase_name(self):
        self.assertEqual(FullyDecoratedTranTestCase.__name__, 'FullyDecoratedTranTestCase')

    def test_decorated_testcase_module(self):
        self.assertEqual(FullyDecoratedTranTestCase.__module__, __name__)


@override_settings(TEST='override')
class FullyDecoratedTestCase(TestCase):

    def test_override(self):
        self.assertEqual(settings.TEST, 'override')

    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertEqual(settings.TEST, 'override2')


class ClassDecoratedTestCaseSuper(TestCase):
    """
    Dummy class for testing max recursion error in child class call to
    super().  Refs #17011.

    """
    def test_max_recursion_error(self):
        pass


@override_settings(TEST='override')
class ClassDecoratedTestCase(ClassDecoratedTestCaseSuper):
    def test_override(self):
        self.assertEqual(settings.TEST, 'override')

    @override_settings(TEST='override2')
    def test_method_override(self):
        self.assertEqual(settings.TEST, 'override2')

    def test_max_recursion_error(self):
        """
        Overriding a method on a super class and then calling that method on
        the super class should not trigger infinite recursion. See #17011.

        """
        try:
            super(ClassDecoratedTestCase, self).test_max_recursion_error()
        except RuntimeError:
            self.fail()


class SettingsTests(TestCase):
    def setUp(self):
        self.testvalue = None
        signals.setting_changed.connect(self.signal_callback)

    def tearDown(self):
        signals.setting_changed.disconnect(self.signal_callback)

    def signal_callback(self, sender, setting, value, **kwargs):
        if setting == 'TEST':
            self.testvalue = value

    def test_override(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
        self.assertEqual('test', settings.TEST)
        del settings.TEST

    def test_override_change(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            settings.TEST = 'test2'
        self.assertEqual('test', settings.TEST)
        del settings.TEST

    def test_override_doesnt_leak(self):
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            settings.TEST = 'test'
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    @override_settings(TEST='override')
    def test_decorator(self):
        self.assertEqual('override', settings.TEST)

    def test_context_manager(self):
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        override = override_settings(TEST='override')
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        override.enable()
        self.assertEqual('override', settings.TEST)
        override.disable()
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    def test_class_decorator(self):
        # TransactionTestCase can be decorated by override_settings, but not ut.TestCase
        class TransactionTestCaseSubclass(TransactionTestCase):
            pass

        class UnittestTestCaseSubclass(unittest.TestCase):
            pass

        decorated = override_settings(TEST='override')(TransactionTestCaseSubclass)
        self.assertIsInstance(decorated, type)
        self.assertTrue(issubclass(decorated, TransactionTestCase))

        with six.assertRaisesRegex(self, Exception,
                "Only subclasses of Django TransactionTestCase*"):
            decorated = override_settings(TEST='override')(UnittestTestCaseSubclass)

    def test_signal_callback_context_manager(self):
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        with self.settings(TEST='override'):
            self.assertEqual(self.testvalue, 'override')
        self.assertEqual(self.testvalue, None)

    @override_settings(TEST='override')
    def test_signal_callback_decorator(self):
        self.assertEqual(self.testvalue, 'override')

    #
    # Regression tests for #10130: deleting settings.
    #

    def test_settings_delete(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        del settings.TEST
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    def test_settings_delete_wrapped(self):
        self.assertRaises(TypeError, delattr, settings, '_wrapped')

    def test_override_settings_delete(self):
        """
        Allow deletion of a setting in an overriden settings set (#18824)
        """
        previous_i18n = settings.USE_I18N
        with self.settings(USE_I18N=False):
            del settings.USE_I18N
            self.assertRaises(AttributeError, getattr, settings, 'USE_I18N')
        self.assertEqual(settings.USE_I18N, previous_i18n)

    def test_allowed_include_roots_string(self):
        """
        ALLOWED_INCLUDE_ROOTS is not allowed to be incorrectly set to a string
        rather than a tuple.
        """
        self.assertRaises(ValueError, setattr, settings,
            'ALLOWED_INCLUDE_ROOTS', '/var/www/ssi/')


class TrailingSlashURLTests(TestCase):
    """
    Tests for the MEDIA_URL and STATIC_URL settings.

    They must end with a slash to ensure there's a deterministic way to build
    paths in templates.
    """
    settings_module = settings

    def setUp(self):
        self._original_media_url = self.settings_module.MEDIA_URL
        self._original_static_url = self.settings_module.STATIC_URL

    def tearDown(self):
        self.settings_module.MEDIA_URL = self._original_media_url
        self.settings_module.STATIC_URL = self._original_static_url

    def test_blank(self):
        """
        The empty string is accepted, even though it doesn't end in a slash.
        """
        self.settings_module.MEDIA_URL = ''
        self.assertEqual('', self.settings_module.MEDIA_URL)

        self.settings_module.STATIC_URL = ''
        self.assertEqual('', self.settings_module.STATIC_URL)

    def test_end_slash(self):
        """
        It works if the value ends in a slash.
        """
        self.settings_module.MEDIA_URL = '/foo/'
        self.assertEqual('/foo/', self.settings_module.MEDIA_URL)

        self.settings_module.MEDIA_URL = 'http://media.foo.com/'
        self.assertEqual('http://media.foo.com/',
                         self.settings_module.MEDIA_URL)

        self.settings_module.STATIC_URL = '/foo/'
        self.assertEqual('/foo/', self.settings_module.STATIC_URL)

        self.settings_module.STATIC_URL = 'http://static.foo.com/'
        self.assertEqual('http://static.foo.com/',
                         self.settings_module.STATIC_URL)

    def test_no_end_slash(self):
        """
        An ImproperlyConfigured exception is raised if the value doesn't end
        in a slash.
        """
        with self.assertRaises(ImproperlyConfigured):
            self.settings_module.MEDIA_URL = '/foo'

        with self.assertRaises(ImproperlyConfigured):
            self.settings_module.MEDIA_URL = 'http://media.foo.com'

        with self.assertRaises(ImproperlyConfigured):
            self.settings_module.STATIC_URL = '/foo'

        with self.assertRaises(ImproperlyConfigured):
            self.settings_module.STATIC_URL = 'http://static.foo.com'

    def test_double_slash(self):
        """
        If the value ends in more than one slash, presume they know what
        they're doing.
        """
        self.settings_module.MEDIA_URL = '/stupid//'
        self.assertEqual('/stupid//', self.settings_module.MEDIA_URL)

        self.settings_module.MEDIA_URL = 'http://media.foo.com/stupid//'
        self.assertEqual('http://media.foo.com/stupid//',
                         self.settings_module.MEDIA_URL)

        self.settings_module.STATIC_URL = '/stupid//'
        self.assertEqual('/stupid//', self.settings_module.STATIC_URL)

        self.settings_module.STATIC_URL = 'http://static.foo.com/stupid//'
        self.assertEqual('http://static.foo.com/stupid//',
                         self.settings_module.STATIC_URL)


class SecureProxySslHeaderTest(TestCase):
    settings_module = settings

    def setUp(self):
        self._original_setting = self.settings_module.SECURE_PROXY_SSL_HEADER

    def tearDown(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = self._original_setting

    def test_none(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = None
        req = HttpRequest()
        self.assertEqual(req.is_secure(), False)

    def test_set_without_xheader(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
        req = HttpRequest()
        self.assertEqual(req.is_secure(), False)

    def test_set_with_xheader_wrong(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
        req = HttpRequest()
        req.META['HTTP_X_FORWARDED_PROTOCOL'] = 'wrongvalue'
        self.assertEqual(req.is_secure(), False)

    def test_set_with_xheader_right(self):
        self.settings_module.SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
        req = HttpRequest()
        req.META['HTTP_X_FORWARDED_PROTOCOL'] = 'https'
        self.assertEqual(req.is_secure(), True)

class EnvironmentVariableTest(TestCase):
    """
    Ensures proper settings file is used in setup_environ if
    DJANGO_SETTINGS_MODULE is set in the environment.
    """
    # Decide what to do with these tests when setup_environ() gets removed in Django 1.6
    def setUp(self):
        self.original_value = os.environ.get('DJANGO_SETTINGS_MODULE')
        self.save_warnings_state()
        warnings.filterwarnings('ignore', category=DeprecationWarning, module='django.core.management')

    def tearDown(self):
        self.restore_warnings_state()
        if self.original_value:
            os.environ['DJANGO_SETTINGS_MODULE'] = self.original_value
        elif 'DJANGO_SETTINGS_MODULE' in os.environ:
            del(os.environ['DJANGO_SETTINGS_MODULE'])

    def test_env_var_used(self):
        """
        If the environment variable is set, do not ignore it. However, the
        kwarg original_settings_path takes precedence.

        This tests both plus the default (neither set).
        """
        from django.core.management import setup_environ

        # whatever was already there
        original_module =  os.environ.get(
            'DJANGO_SETTINGS_MODULE',
            'the default'
        )

        # environment variable set by user
        user_override = 'custom.settings'

        # optional argument to setup_environ
        orig_path = 'original.path'

        # expect default
        setup_environ(global_settings)
        self.assertEqual(
            os.environ.get('DJANGO_SETTINGS_MODULE'),
            original_module
        )

        # override with environment variable
        os.environ['DJANGO_SETTINGS_MODULE'] = user_override
        setup_environ(global_settings)

        self.assertEqual(
            os.environ.get('DJANGO_SETTINGS_MODULE'),
            user_override
        )

        # pass in original_settings_path (should take precedence)
        os.environ['DJANGO_SETTINGS_MODULE'] = user_override
        setup_environ(global_settings, original_settings_path = orig_path)

        self.assertEqual(
            os.environ.get('DJANGO_SETTINGS_MODULE'),
            orig_path
        )
