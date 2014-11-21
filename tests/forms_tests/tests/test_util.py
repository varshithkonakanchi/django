# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

from django.core.exceptions import ValidationError
from django.forms.utils import flatatt, ErrorDict, ErrorList
from django.test import TestCase
from django.utils.safestring import mark_safe
from django.utils import six
from django.utils.translation import ugettext_lazy
from django.utils.encoding import python_2_unicode_compatible


class FormsUtilTestCase(TestCase):
    # Tests for forms/utils.py module.

    def test_flatatt(self):
        ###########
        # flatatt #
        ###########

        self.assertEqual(flatatt({'id': "header"}), ' id="header"')
        self.assertEqual(flatatt({'class': "news", 'title': "Read this"}), ' class="news" title="Read this"')
        self.assertEqual(flatatt({'class': "news", 'title': "Read this", 'required': "required"}), ' class="news" required="required" title="Read this"')
        self.assertEqual(flatatt({'class': "news", 'title': "Read this", 'required': True}), ' class="news" title="Read this" required')
        self.assertEqual(flatatt({'class': "news", 'title': "Read this", 'required': False}), ' class="news" title="Read this"')
        self.assertEqual(flatatt({}), '')

    def test_flatatt_no_side_effects(self):
        """
        Fixes #23883 -- Check that flatatt does not modify the dict passed in
        """
        attrs = {'foo': 'bar', 'true': True, 'false': False}
        attrs_copy = copy.copy(attrs)
        self.assertEqual(attrs, attrs_copy)

        first_run = flatatt(attrs)
        self.assertEqual(attrs, attrs_copy)
        self.assertEqual(first_run, ' foo="bar" true')

        second_run = flatatt(attrs)
        self.assertEqual(attrs, attrs_copy)

        self.assertEqual(first_run, second_run)

    def test_validation_error(self):
        ###################
        # ValidationError #
        ###################

        # Can take a string.
        self.assertHTMLEqual(str(ErrorList(ValidationError("There was an error.").messages)),
                         '<ul class="errorlist"><li>There was an error.</li></ul>')

        # Can take a unicode string.
        self.assertHTMLEqual(six.text_type(ErrorList(ValidationError("Not \u03C0.").messages)),
                         '<ul class="errorlist"><li>Not π.</li></ul>')

        # Can take a lazy string.
        self.assertHTMLEqual(str(ErrorList(ValidationError(ugettext_lazy("Error.")).messages)),
                         '<ul class="errorlist"><li>Error.</li></ul>')

        # Can take a list.
        self.assertHTMLEqual(str(ErrorList(ValidationError(["Error one.", "Error two."]).messages)),
                         '<ul class="errorlist"><li>Error one.</li><li>Error two.</li></ul>')

        # Can take a mixture in a list.
        self.assertHTMLEqual(str(ErrorList(ValidationError(["First error.", "Not \u03C0.", ugettext_lazy("Error.")]).messages)),
                         '<ul class="errorlist"><li>First error.</li><li>Not π.</li><li>Error.</li></ul>')

        @python_2_unicode_compatible
        class VeryBadError:
            def __str__(self):
                return "A very bad error."

        # Can take a non-string.
        self.assertHTMLEqual(str(ErrorList(ValidationError(VeryBadError()).messages)),
                         '<ul class="errorlist"><li>A very bad error.</li></ul>')

        # Escapes non-safe input but not input marked safe.
        example = 'Example of link: <a href="http://www.example.com/">example</a>'
        self.assertHTMLEqual(str(ErrorList([example])),
                         '<ul class="errorlist"><li>Example of link: &lt;a href=&quot;http://www.example.com/&quot;&gt;example&lt;/a&gt;</li></ul>')
        self.assertHTMLEqual(str(ErrorList([mark_safe(example)])),
                         '<ul class="errorlist"><li>Example of link: <a href="http://www.example.com/">example</a></li></ul>')
        self.assertHTMLEqual(str(ErrorDict({'name': example})),
                         '<ul class="errorlist"><li>nameExample of link: &lt;a href=&quot;http://www.example.com/&quot;&gt;example&lt;/a&gt;</li></ul>')
        self.assertHTMLEqual(str(ErrorDict({'name': mark_safe(example)})),
                         '<ul class="errorlist"><li>nameExample of link: <a href="http://www.example.com/">example</a></li></ul>')

    def test_error_dict_copy(self):
        e = ErrorDict()
        e['__all__'] = ErrorList([
            ValidationError(
                message='message %(i)s',
                params={'i': 1},
            ),
            ValidationError(
                message='message %(i)s',
                params={'i': 2},
            ),
        ])

        e_copy = copy.copy(e)
        self.assertEqual(e, e_copy)
        self.assertEqual(e.as_data(), e_copy.as_data())

        e_deepcopy = copy.deepcopy(e)
        self.assertEqual(e, e_deepcopy)
        self.assertEqual(e.as_data(), e_copy.as_data())
