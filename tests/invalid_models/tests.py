import sys
import unittest

from django.core.apps import app_cache
from django.core.management.validation import get_validation_errors
from django.test.utils import override_settings
from django.utils.six import StringIO


class InvalidModelTestCase(unittest.TestCase):
    """Import an appliation with invalid models and test the exceptions."""

    def setUp(self):
        # Make sure sys.stdout is not a tty so that we get errors without
        # coloring attached (makes matching the results easier). We restore
        # sys.stderr afterwards.
        self.old_stdout = sys.stdout
        self.stdout = StringIO()
        sys.stdout = self.stdout

        # The models need to be removed after the test in order to prevent bad
        # interactions with the flush operation in other tests.
        self._old_models = app_cache.app_configs['invalid_models'].models.copy()

    def tearDown(self):
        app_cache.app_configs['invalid_models'].models = self._old_models
        app_cache._get_models_cache = {}
        sys.stdout = self.old_stdout

    # Technically, this isn't an override -- TEST_SWAPPED_MODEL must be
    # set to *something* in order for the test to work. However, it's
    # easier to set this up as an override than to require every developer
    # to specify a value in their test settings.
    @override_settings(
        TEST_SWAPPED_MODEL='invalid_models.ReplacementModel',
        TEST_SWAPPED_MODEL_BAD_VALUE='not-a-model',
        TEST_SWAPPED_MODEL_BAD_MODEL='not_an_app.Target',
    )
    def test_invalid_models(self):
        try:
            module = app_cache.load_app("invalid_models.invalid_models")
        except Exception:
            self.fail('Unable to load invalid model module')

        get_validation_errors(self.stdout, module)
        self.stdout.seek(0)
        error_log = self.stdout.read()
        actual = error_log.split('\n')
        expected = module.model_errors.split('\n')

        unexpected = [err for err in actual if err not in expected]
        missing = [err for err in expected if err not in actual]
        self.assertFalse(unexpected, "Unexpected Errors: " + '\n'.join(unexpected))
        self.assertFalse(missing, "Missing Errors: " + '\n'.join(missing))
