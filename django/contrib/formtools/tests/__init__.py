import os
import warnings

from django import forms, http
from django.conf import settings
from django.contrib.formtools import preview, wizard, utils
from django.test import TestCase
from django.test.utils import get_warnings_state, restore_warnings_state
from django.utils import unittest


success_string = "Done was called!"

class TestFormPreview(preview.FormPreview):
    def get_context(self, request, form):
        context = super(TestFormPreview, self).get_context(request, form)
        context.update({'custom_context': True})
        return context

    def get_initial(self, request):
        return {'field1': 'Works!'}

    def done(self, request, cleaned_data):
        return http.HttpResponse(success_string)


class TestForm(forms.Form):
    field1 = forms.CharField()
    field1_ = forms.CharField()
    bool1 = forms.BooleanField(required=False)


class PreviewTests(TestCase):
    urls = 'django.contrib.formtools.tests.urls'

    def setUp(self):
        self.save_warnings_state()
        warnings.filterwarnings('ignore', category=DeprecationWarning,
                                module='django.contrib.formtools.utils')

        # Create a FormPreview instance to share between tests
        self.preview = preview.FormPreview(TestForm)
        input_template = '<input type="hidden" name="%s" value="%s" />'
        self.input = input_template % (self.preview.unused_name('stage'), "%d")
        self.test_data = {'field1':u'foo', 'field1_':u'asdf'}

    def tearDown(self):
        self.restore_warnings_state()

    def test_unused_name(self):
        """
        Verifies name mangling to get uniue field name.
        """
        self.assertEqual(self.preview.unused_name('field1'), 'field1__')

    def test_form_get(self):
        """
        Test contrib.formtools.preview form retrieval.

        Use the client library to see if we can sucessfully retrieve
        the form (mostly testing the setup ROOT_URLCONF
        process). Verify that an additional  hidden input field
        is created to manage the stage.

        """
        response = self.client.get('/test1/')
        stage = self.input % 1
        self.assertContains(response, stage, 1)
        self.assertEqual(response.context['custom_context'], True)
        self.assertEqual(response.context['form'].initial, {'field1': 'Works!'})

    def test_form_preview(self):
        """
        Test contrib.formtools.preview form preview rendering.

        Use the client library to POST to the form to see if a preview
        is returned.  If we do get a form back check that the hidden
        value is correctly managing the state of the form.

        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        self.test_data.update({'stage': 1})
        response = self.client.post('/test1/', self.test_data)
        # Check to confirm stage is set to 2 in output form.
        stage = self.input % 2
        self.assertContains(response, stage, 1)

    def test_form_submit(self):
        """
        Test contrib.formtools.preview form submittal.

        Use the client library to POST to the form with stage set to 3
        to see if our forms done() method is called. Check first
        without the security hash, verify failure, retry with security
        hash and verify sucess.

        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        self.test_data.update({'stage':2})
        response = self.client.post('/test1/', self.test_data)
        self.assertNotEqual(response.content, success_string)
        hash = self.preview.security_hash(None, TestForm(self.test_data))
        self.test_data.update({'hash': hash})
        response = self.client.post('/test1/', self.test_data)
        self.assertEqual(response.content, success_string)

    def test_bool_submit(self):
        """
        Test contrib.formtools.preview form submittal when form contains:
        BooleanField(required=False)

        Ticket: #6209 - When an unchecked BooleanField is previewed, the preview
        form's hash would be computed with no value for ``bool1``. However, when
        the preview form is rendered, the unchecked hidden BooleanField would be
        rendered with the string value 'False'. So when the preview form is
        resubmitted, the hash would be computed with the value 'False' for
        ``bool1``. We need to make sure the hashes are the same in both cases.

        """
        self.test_data.update({'stage':2})
        hash = self.preview.security_hash(None, TestForm(self.test_data))
        self.test_data.update({'hash':hash, 'bool1':u'False'})
        response = self.client.post('/test1/', self.test_data)
        self.assertEqual(response.content, success_string)

    def test_form_submit_good_hash(self):
        """
        Test contrib.formtools.preview form submittal, using a correct
        hash
        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        self.test_data.update({'stage':2})
        response = self.client.post('/test1/', self.test_data)
        self.assertNotEqual(response.content, success_string)
        hash = utils.form_hmac(TestForm(self.test_data))
        self.test_data.update({'hash': hash})
        response = self.client.post('/test1/', self.test_data)
        self.assertEqual(response.content, success_string)


    def test_form_submit_bad_hash(self):
        """
        Test contrib.formtools.preview form submittal does not proceed
        if the hash is incorrect.
        """
        # Pass strings for form submittal and add stage variable to
        # show we previously saw first stage of the form.
        self.test_data.update({'stage':2})
        response = self.client.post('/test1/', self.test_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.content, success_string)
        hash = utils.form_hmac(TestForm(self.test_data)) + "bad"
        self.test_data.update({'hash': hash})
        response = self.client.post('/test1/', self.test_data)
        self.assertNotEqual(response.content, success_string)


class SecurityHashTests(unittest.TestCase):
    def setUp(self):
        self._warnings_state = get_warnings_state()
        warnings.filterwarnings('ignore', category=DeprecationWarning,
                                module='django.contrib.formtools.utils')

    def tearDown(self):
        restore_warnings_state(self._warnings_state)

    def test_textfield_hash(self):
        """
        Regression test for #10034: the hash generation function should ignore
        leading/trailing whitespace so as to be friendly to broken browsers that
        submit it (usually in textareas).
        """
        f1 = HashTestForm({'name': 'joe', 'bio': 'Nothing notable.'})
        f2 = HashTestForm({'name': '  joe', 'bio': 'Nothing notable.  '})
        hash1 = utils.security_hash(None, f1)
        hash2 = utils.security_hash(None, f2)
        self.assertEqual(hash1, hash2)

    def test_empty_permitted(self):
        """
        Regression test for #10643: the security hash should allow forms with
        empty_permitted = True, or forms where data has not changed.
        """
        f1 = HashTestBlankForm({})
        f2 = HashTestForm({}, empty_permitted=True)
        hash1 = utils.security_hash(None, f1)
        hash2 = utils.security_hash(None, f2)
        self.assertEqual(hash1, hash2)


class FormHmacTests(unittest.TestCase):
    """
    Same as SecurityHashTests, but with form_hmac
    """

    def test_textfield_hash(self):
        """
        Regression test for #10034: the hash generation function should ignore
        leading/trailing whitespace so as to be friendly to broken browsers that
        submit it (usually in textareas).
        """
        f1 = HashTestForm({'name': 'joe', 'bio': 'Nothing notable.'})
        f2 = HashTestForm({'name': '  joe', 'bio': 'Nothing notable.  '})
        hash1 = utils.form_hmac(f1)
        hash2 = utils.form_hmac(f2)
        self.assertEqual(hash1, hash2)

    def test_empty_permitted(self):
        """
        Regression test for #10643: the security hash should allow forms with
        empty_permitted = True, or forms where data has not changed.
        """
        f1 = HashTestBlankForm({})
        f2 = HashTestForm({}, empty_permitted=True)
        hash1 = utils.form_hmac(f1)
        hash2 = utils.form_hmac(f2)
        self.assertEqual(hash1, hash2)


class HashTestForm(forms.Form):
    name = forms.CharField()
    bio = forms.CharField()


class HashTestBlankForm(forms.Form):
    name = forms.CharField(required=False)
    bio = forms.CharField(required=False)

#
# FormWizard tests
#


class WizardPageOneForm(forms.Form):
    field = forms.CharField()


class WizardPageTwoForm(forms.Form):
    field = forms.CharField()

class WizardPageTwoAlternativeForm(forms.Form):
    field = forms.CharField()

class WizardPageThreeForm(forms.Form):
    field = forms.CharField()


class WizardClass(wizard.FormWizard):

    def get_template(self, step):
        return 'formwizard/wizard.html'

    def done(self, request, cleaned_data):
        return http.HttpResponse(success_string)


class DummyRequest(http.HttpRequest):

    def __init__(self, POST=None):
        super(DummyRequest, self).__init__()
        self.method = POST and "POST" or "GET"
        if POST is not None:
            self.POST.update(POST)
        self._dont_enforce_csrf_checks = True


class WizardTests(TestCase):
    urls = 'django.contrib.formtools.tests.urls'

    def setUp(self):
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(
                os.path.dirname(__file__),
                'templates'
            ),
        )
        # Use a known SECRET_KEY to make security_hash tests deterministic
        self.old_SECRET_KEY = settings.SECRET_KEY
        settings.SECRET_KEY = "123"

    def tearDown(self):
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS
        settings.SECRET_KEY = self.old_SECRET_KEY

    def test_step_starts_at_zero(self):
        """
        step should be zero for the first form
        """
        response = self.client.get('/wizard/')
        self.assertEqual(0, response.context['step0'])

    def test_step_increments(self):
        """
        step should be incremented when we go to the next page
        """
        response = self.client.post('/wizard/', {"0-field":"test", "wizard_step":"0"})
        self.assertEqual(1, response.context['step0'])

    def test_bad_hash(self):
        """
        Form should not advance if the hash is missing or bad
        """
        response = self.client.post('/wizard/',
                                    {"0-field":"test",
                                     "1-field":"test2",
                                     "wizard_step": "1"})
        self.assertEqual(0, response.context['step0'])

    def test_good_hash(self):
        """
        Form should advance if the hash is present and good, as calculated using
        current method.
        """
        data = {"0-field": "test",
                "1-field": "test2",
                "hash_0": "7e9cea465f6a10a6fb47fcea65cb9a76350c9a5c",
                "wizard_step": "1"}
        response = self.client.post('/wizard/', data)
        self.assertEqual(2, response.context['step0'])

    def test_14498(self):
        """
        Regression test for ticket #14498.  All previous steps' forms should be
        validated.
        """
        reached = [False]
        that = self

        class WizardWithProcessStep(WizardClass):
            def process_step(self, request, form, step):
                that.assertTrue(hasattr(form, 'cleaned_data'))
                reached[0] = True

        wizard = WizardWithProcessStep([WizardPageOneForm,
                                        WizardPageTwoForm,
                                        WizardPageThreeForm])
        data = {"0-field": "test",
                "1-field": "test2",
                "hash_0": "7e9cea465f6a10a6fb47fcea65cb9a76350c9a5c",
                "wizard_step": "1"}
        wizard(DummyRequest(POST=data))
        self.assertTrue(reached[0])

    def test_14576(self):
        """
        Regression test for ticket #14576.

        The form of the last step is not passed to the done method.
        """
        reached = [False]
        that = self

        class Wizard(WizardClass):
            def done(self, request, form_list):
                reached[0] = True
                that.assertTrue(len(form_list) == 2)

        wizard = Wizard([WizardPageOneForm,
                         WizardPageTwoForm])

        data = {"0-field": "test",
                "1-field": "test2",
                "hash_0": "7e9cea465f6a10a6fb47fcea65cb9a76350c9a5c",
                "wizard_step": "1"}
        wizard(DummyRequest(POST=data))
        self.assertTrue(reached[0])

    def test_15075(self):
        """
        Regression test for ticket #15075.  Allow modifying wizard's form_list
        in process_step.
        """
        reached = [False]
        that = self

        class WizardWithProcessStep(WizardClass):
            def process_step(self, request, form, step):
                if step == 0:
                    self.form_list[1] = WizardPageTwoAlternativeForm
                if step == 1:
                    that.assertTrue(isinstance(form, WizardPageTwoAlternativeForm))
                    reached[0] = True

        wizard = WizardWithProcessStep([WizardPageOneForm,
                                        WizardPageTwoForm,
                                        WizardPageThreeForm])
        data = {"0-field": "test",
                "1-field": "test2",
                "hash_0": "7e9cea465f6a10a6fb47fcea65cb9a76350c9a5c",
                "wizard_step": "1"}
        wizard(DummyRequest(POST=data))
        self.assertTrue(reached[0])
