# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import io
import os
import re
import shutil
import sys
import time
from unittest import SkipTest, skipUnless
import warnings

from django.conf import settings
from django.core import management
from django.core.management import execute_from_command_line
from django.core.management.utils import find_command
from django.test import SimpleTestCase
from django.test import override_settings
from django.utils.encoding import force_text
from django.utils._os import upath
from django.utils import six
from django.utils.six import StringIO
from django.utils.translation import TranslatorCommentWarning


LOCALE = 'de'
has_xgettext = find_command('xgettext')
this_directory = os.path.dirname(upath(__file__))


@skipUnless(has_xgettext, 'xgettext is mandatory for extraction tests')
class ExtractorTests(SimpleTestCase):

    test_dir = os.path.abspath(os.path.join(this_directory, 'commands'))

    PO_FILE = 'locale/%s/LC_MESSAGES/django.po' % LOCALE

    def setUp(self):
        self._cwd = os.getcwd()

    def _rmrf(self, dname):
        if os.path.commonprefix([self.test_dir, os.path.abspath(dname)]) != self.test_dir:
            return
        shutil.rmtree(dname)

    def rmfile(self, filepath):
        if os.path.exists(filepath):
            os.remove(filepath)

    def tearDown(self):
        os.chdir(self.test_dir)
        try:
            self._rmrf('locale/%s' % LOCALE)
        except OSError:
            pass
        os.chdir(self._cwd)

    def _run_makemessages(self, **options):
        os.chdir(self.test_dir)
        out = StringIO()
        management.call_command('makemessages', locale=[LOCALE], verbosity=2,
            stdout=out, **options)
        output = out.getvalue()
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = fp.read()
        return output, po_contents

    def assertMsgId(self, msgid, s, use_quotes=True):
        q = '"'
        if use_quotes:
            msgid = '"%s"' % msgid
            q = "'"
        needle = 'msgid %s' % msgid
        msgid = re.escape(msgid)
        return self.assertTrue(re.search('^msgid %s' % msgid, s, re.MULTILINE), 'Could not find %(q)s%(n)s%(q)s in generated PO file' % {'n': needle, 'q': q})

    def assertNotMsgId(self, msgid, s, use_quotes=True):
        if use_quotes:
            msgid = '"%s"' % msgid
        msgid = re.escape(msgid)
        return self.assertTrue(not re.search('^msgid %s' % msgid, s, re.MULTILINE))

    def _assertPoLocComment(self, assert_presence, po_filename, line_number, *comment_parts):
        with open(po_filename, 'r') as fp:
            po_contents = force_text(fp.read())
        if os.name == 'nt':
            # #: .\path\to\file.html:123
            cwd_prefix = '%s%s' % (os.curdir, os.sep)
        else:
            # #: path/to/file.html:123
            cwd_prefix = ''
        parts = ['#: ']
        parts.append(os.path.join(cwd_prefix, *comment_parts))
        if line_number is not None:
            parts.append(':%d' % line_number)
        needle = ''.join(parts)
        if assert_presence:
            return self.assertTrue(needle in po_contents, '"%s" not found in final .po file.' % needle)
        else:
            return self.assertFalse(needle in po_contents, '"%s" shouldn\'t be in final .po file.' % needle)

    def assertLocationCommentPresent(self, po_filename, line_number, *comment_parts):
        """
        self.assertLocationCommentPresent('django.po', 42, 'dirA', 'dirB', 'foo.py')

        verifies that the django.po file has a gettext-style location comment of the form

        `#: dirA/dirB/foo.py:42`

        (or `#: .\dirA\dirB\foo.py:42` on Windows)

        None can be passed for the line_number argument to skip checking of the :42 suffix part.
        """
        return self._assertPoLocComment(True, po_filename, line_number, *comment_parts)

    def assertLocationCommentNotPresent(self, po_filename, line_number, *comment_parts):
        """Check the opposite of assertLocationComment()"""
        return self._assertPoLocComment(False, po_filename, line_number, *comment_parts)

    def assertRecentlyModified(self, path):
        """
        Assert that file was recently modified (modification time was less than 10 seconds ago).
        """
        delta = time.time() - os.stat(path).st_mtime
        self.assertLess(delta, 10, "%s was recently modified" % path)

    def assertNotRecentlyModified(self, path):
        """
        Assert that file was not recently modified (modification time was more than 10 seconds ago).
        """
        delta = time.time() - os.stat(path).st_mtime
        self.assertGreater(delta, 10, "%s wasn't recently modified" % path)


class BasicExtractorTests(ExtractorTests):

    def test_comments_extractor(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with io.open(self.PO_FILE, 'r', encoding='utf-8') as fp:
            po_contents = fp.read()
            self.assertTrue('#. Translators: This comment should be extracted' in po_contents)
            self.assertTrue('This comment should not be extracted' not in po_contents)
            # Comments in templates
            self.assertTrue('#. Translators: Django template comment for translators' in po_contents)
            self.assertTrue("#. Translators: Django comment block for translators\n#. string's meaning unveiled" in po_contents)

            self.assertTrue('#. Translators: One-line translator comment #1' in po_contents)
            self.assertTrue('#. Translators: Two-line translator comment #1\n#. continued here.' in po_contents)

            self.assertTrue('#. Translators: One-line translator comment #2' in po_contents)
            self.assertTrue('#. Translators: Two-line translator comment #2\n#. continued here.' in po_contents)

            self.assertTrue('#. Translators: One-line translator comment #3' in po_contents)
            self.assertTrue('#. Translators: Two-line translator comment #3\n#. continued here.' in po_contents)

            self.assertTrue('#. Translators: One-line translator comment #4' in po_contents)
            self.assertTrue('#. Translators: Two-line translator comment #4\n#. continued here.' in po_contents)

            self.assertTrue('#. Translators: One-line translator comment #5 -- with non ASCII characters: áéíóúö' in po_contents)
            self.assertTrue('#. Translators: Two-line translator comment #5 -- with non ASCII characters: áéíóúö\n#. continued here.' in po_contents)

    def test_templatize_trans_tag(self):
        # ticket #11240
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('Literal with a percent symbol at the end %%', po_contents)
            self.assertMsgId('Literal with a percent %% symbol in the middle', po_contents)
            self.assertMsgId('Completed 50%% of all the tasks', po_contents)
            self.assertMsgId('Completed 99%% of all the tasks', po_contents)
            self.assertMsgId("Shouldn't double escape this sequence: %% (two percent signs)", po_contents)
            self.assertMsgId("Shouldn't double escape this sequence %% either", po_contents)
            self.assertMsgId("Looks like a str fmt spec %%s but shouldn't be interpreted as such", po_contents)
            self.assertMsgId("Looks like a str fmt spec %% o but shouldn't be interpreted as such", po_contents)

    def test_templatize_blocktrans_tag(self):
        # ticket #11966
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('I think that 100%% is more that 50%% of anything.', po_contents)
            self.assertMsgId('I think that 100%% is more that 50%% of %(obj)s.', po_contents)
            self.assertMsgId("Blocktrans extraction shouldn't double escape this: %%, a=%(a)s", po_contents)

    def test_blocktrans_trimmed(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            # should not be trimmed
            self.assertNotMsgId('Text with a few line breaks.', po_contents)
            # should be trimmed
            self.assertMsgId("Again some text with a few line breaks, this time should be trimmed.", po_contents)
        # #21406 -- Should adjust for eaten line numbers
        self.assertMsgId("I'm on line 97", po_contents)
        self.assertLocationCommentPresent(self.PO_FILE, 97, 'templates', 'test.html')

    def test_force_en_us_locale(self):
        """Value of locale-munging option used by the command is the right one"""
        from django.core.management.commands.makemessages import Command
        self.assertTrue(Command.leave_locale_alone)

    def test_extraction_error(self):
        os.chdir(self.test_dir)
        self.assertRaises(SyntaxError, management.call_command, 'makemessages', locale=[LOCALE], extensions=['tpl'], verbosity=0)
        with self.assertRaises(SyntaxError) as context_manager:
            management.call_command('makemessages', locale=[LOCALE], extensions=['tpl'], verbosity=0)
        six.assertRegex(
            self, str(context_manager.exception),
            r'Translation blocks must not include other block tags: blocktrans \(file templates[/\\]template_with_error\.tpl, line 3\)'
        )
        # Check that the temporary file was cleaned up
        self.assertFalse(os.path.exists('./templates/template_with_error.tpl.py'))

    def test_unicode_decode_error(self):
        os.chdir(self.test_dir)
        shutil.copyfile('./not_utf8.sample', './not_utf8.txt')
        self.addCleanup(self.rmfile, os.path.join(self.test_dir, 'not_utf8.txt'))
        out = StringIO()
        management.call_command('makemessages', locale=[LOCALE], stdout=out)
        self.assertIn("UnicodeDecodeError: skipped file not_utf8.txt in .",
                      force_text(out.getvalue()))

    def test_extraction_warning(self):
        """test xgettext warning about multiple bare interpolation placeholders"""
        os.chdir(self.test_dir)
        shutil.copyfile('./code.sample', './code_sample.py')
        self.addCleanup(self.rmfile, os.path.join(self.test_dir, 'code_sample.py'))
        out = StringIO()
        management.call_command('makemessages', locale=[LOCALE], stdout=out)
        self.assertIn("code_sample.py:4", force_text(out.getvalue()))

    def test_template_message_context_extractor(self):
        """
        Ensure that message contexts are correctly extracted for the
        {% trans %} and {% blocktrans %} template tags.
        Refs #14806.
        """
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            # {% trans %}
            self.assertTrue('msgctxt "Special trans context #1"' in po_contents)
            self.assertMsgId("Translatable literal #7a", po_contents)
            self.assertTrue('msgctxt "Special trans context #2"' in po_contents)
            self.assertMsgId("Translatable literal #7b", po_contents)
            self.assertTrue('msgctxt "Special trans context #3"' in po_contents)
            self.assertMsgId("Translatable literal #7c", po_contents)

            # {% blocktrans %}
            self.assertTrue('msgctxt "Special blocktrans context #1"' in po_contents)
            self.assertMsgId("Translatable literal #8a", po_contents)
            self.assertTrue('msgctxt "Special blocktrans context #2"' in po_contents)
            self.assertMsgId("Translatable literal #8b-singular", po_contents)
            self.assertTrue("Translatable literal #8b-plural" in po_contents)
            self.assertTrue('msgctxt "Special blocktrans context #3"' in po_contents)
            self.assertMsgId("Translatable literal #8c-singular", po_contents)
            self.assertTrue("Translatable literal #8c-plural" in po_contents)
            self.assertTrue('msgctxt "Special blocktrans context #4"' in po_contents)
            self.assertMsgId("Translatable literal #8d %(a)s", po_contents)

    def test_context_in_single_quotes(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            # {% trans %}
            self.assertTrue('msgctxt "Context wrapped in double quotes"' in po_contents)
            self.assertTrue('msgctxt "Context wrapped in single quotes"' in po_contents)

            # {% blocktrans %}
            self.assertTrue('msgctxt "Special blocktrans context wrapped in double quotes"' in po_contents)
            self.assertTrue('msgctxt "Special blocktrans context wrapped in single quotes"' in po_contents)

    def test_template_comments(self):
        """Template comment tags on the same line of other constructs (#19552)"""
        os.chdir(self.test_dir)
        # Test detection/end user reporting of old, incorrect templates
        # translator comments syntax
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always')
            management.call_command('makemessages', locale=[LOCALE], extensions=['thtml'], verbosity=0)
            self.assertEqual(len(ws), 3)
            for w in ws:
                self.assertTrue(issubclass(w.category, TranslatorCommentWarning))
            six.assertRegex(
                self, str(ws[0].message),
                r"The translator-targeted comment 'Translators: ignored i18n comment #1' \(file templates[/\\]comments.thtml, line 4\) was ignored, because it wasn't the last item on the line\."
            )
            six.assertRegex(
                self, str(ws[1].message),
                r"The translator-targeted comment 'Translators: ignored i18n comment #3' \(file templates[/\\]comments.thtml, line 6\) was ignored, because it wasn't the last item on the line\."
            )
            six.assertRegex(
                self, str(ws[2].message),
                r"The translator-targeted comment 'Translators: ignored i18n comment #4' \(file templates[/\\]comments.thtml, line 8\) was ignored, because it wasn't the last item on the line\."
            )
        # Now test .po file contents
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())

            self.assertMsgId('Translatable literal #9a', po_contents)
            self.assertFalse('ignored comment #1' in po_contents)

            self.assertFalse('Translators: ignored i18n comment #1' in po_contents)
            self.assertMsgId("Translatable literal #9b", po_contents)

            self.assertFalse('ignored i18n comment #2' in po_contents)
            self.assertFalse('ignored comment #2' in po_contents)
            self.assertMsgId('Translatable literal #9c', po_contents)

            self.assertFalse('ignored comment #3' in po_contents)
            self.assertFalse('ignored i18n comment #3' in po_contents)
            self.assertMsgId('Translatable literal #9d', po_contents)

            self.assertFalse('ignored comment #4' in po_contents)
            self.assertMsgId('Translatable literal #9e', po_contents)
            self.assertFalse('ignored comment #5' in po_contents)

            self.assertFalse('ignored i18n comment #4' in po_contents)
            self.assertMsgId('Translatable literal #9f', po_contents)
            self.assertTrue('#. Translators: valid i18n comment #5' in po_contents)

            self.assertMsgId('Translatable literal #9g', po_contents)
            self.assertTrue('#. Translators: valid i18n comment #6' in po_contents)
            self.assertMsgId('Translatable literal #9h', po_contents)
            self.assertTrue('#. Translators: valid i18n comment #7' in po_contents)
            self.assertMsgId('Translatable literal #9i', po_contents)

            six.assertRegex(self, po_contents, r'#\..+Translators: valid i18n comment #8')
            six.assertRegex(self, po_contents, r'#\..+Translators: valid i18n comment #9')
            self.assertMsgId("Translatable literal #9j", po_contents)


class JavascriptExtractorTests(ExtractorTests):

    PO_FILE = 'locale/%s/LC_MESSAGES/djangojs.po' % LOCALE

    def test_javascript_literals(self):
        os.chdir(self.test_dir)
        _, po_contents = self._run_makemessages(domain='djangojs')
        self.assertMsgId('This literal should be included.', po_contents)
        self.assertMsgId('This one as well.', po_contents)
        self.assertMsgId(r'He said, \"hello\".', po_contents)
        self.assertMsgId("okkkk", po_contents)
        self.assertMsgId("TEXT", po_contents)
        self.assertMsgId("It's at http://example.com", po_contents)
        self.assertMsgId("String", po_contents)
        self.assertMsgId("/* but this one will be too */ 'cause there is no way of telling...", po_contents)
        self.assertMsgId("foo", po_contents)
        self.assertMsgId("bar", po_contents)
        self.assertMsgId("baz", po_contents)
        self.assertMsgId("quz", po_contents)
        self.assertMsgId("foobar", po_contents)

    @override_settings(
        STATIC_ROOT=os.path.join(this_directory, 'commands', 'static/'),
        MEDIA_ROOT=os.path.join(this_directory, 'commands', 'media_root/'))
    def test_media_static_dirs_ignored(self):
        """
        Regression test for #23583.
        """
        _, po_contents = self._run_makemessages(domain='djangojs')
        self.assertMsgId("Static content inside app should be included.", po_contents)
        self.assertNotMsgId("Content from STATIC_ROOT should not be included", po_contents)


class IgnoredExtractorTests(ExtractorTests):

    def test_ignore_directory(self):
        out, po_contents = self._run_makemessages(ignore_patterns=[
            os.path.join('ignore_dir', '*'),
        ])
        self.assertTrue("ignoring directory ignore_dir" in out)
        self.assertMsgId('This literal should be included.', po_contents)
        self.assertNotMsgId('This should be ignored.', po_contents)

    def test_ignore_subdirectory(self):
        out, po_contents = self._run_makemessages(ignore_patterns=[
            'templates/*/ignore.html',
            'templates/subdir/*',
        ])
        self.assertTrue("ignoring directory subdir" in out)
        self.assertNotMsgId('This subdir should be ignored too.', po_contents)

    def test_ignore_file_patterns(self):
        out, po_contents = self._run_makemessages(ignore_patterns=[
            'xxx_*',
        ])
        self.assertTrue("ignoring file xxx_ignored.html" in out)
        self.assertNotMsgId('This should be ignored too.', po_contents)

    @override_settings(
        STATIC_ROOT=os.path.join(this_directory, 'commands', 'static/'),
        MEDIA_ROOT=os.path.join(this_directory, 'commands', 'media_root/'))
    def test_media_static_dirs_ignored(self):
        out, _ = self._run_makemessages()
        self.assertIn("ignoring directory static", out)
        self.assertIn("ignoring directory media_root", out)


class SymlinkExtractorTests(ExtractorTests):

    def setUp(self):
        super(SymlinkExtractorTests, self).setUp()
        self.symlinked_dir = os.path.join(self.test_dir, 'templates_symlinked')

    def tearDown(self):
        super(SymlinkExtractorTests, self).tearDown()
        os.chdir(self.test_dir)
        try:
            os.remove(self.symlinked_dir)
        except OSError:
            pass
        os.chdir(self._cwd)

    def test_symlink(self):
        # On Python < 3.2 os.symlink() exists only on Unix
        if hasattr(os, 'symlink'):
            if os.path.exists(self.symlinked_dir):
                self.assertTrue(os.path.islink(self.symlinked_dir))
            else:
                # On Python >= 3.2) os.symlink() exists always but then can
                # fail at runtime when user hasn't the needed permissions on
                # WIndows versions that support symbolink links (>= 6/Vista).
                # See Python issue 9333 (http://bugs.python.org/issue9333).
                # Skip the test in that case
                try:
                    os.symlink(os.path.join(self.test_dir, 'templates'), self.symlinked_dir)
                except (OSError, NotImplementedError):
                    raise SkipTest("os.symlink() is available on this OS but can't be used by this user.")
            os.chdir(self.test_dir)
            management.call_command('makemessages', locale=[LOCALE], verbosity=0, symlinks=True)
            self.assertTrue(os.path.exists(self.PO_FILE))
            with open(self.PO_FILE, 'r') as fp:
                po_contents = force_text(fp.read())
                self.assertMsgId('This literal should be included.', po_contents)
                self.assertTrue('templates_symlinked/test.html' in po_contents)


class CopyPluralFormsExtractorTests(ExtractorTests):

    PO_FILE_ES = 'locale/es/LC_MESSAGES/django.po'

    def tearDown(self):
        super(CopyPluralFormsExtractorTests, self).tearDown()
        os.chdir(self.test_dir)
        try:
            self._rmrf('locale/es')
        except OSError:
            pass
        os.chdir(self._cwd)

    def test_copy_plural_forms(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertTrue('Plural-Forms: nplurals=2; plural=(n != 1)' in po_contents)

    def test_override_plural_forms(self):
        """Ticket #20311."""
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=['es'], extensions=['djtpl'], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_ES))
        with io.open(self.PO_FILE_ES, 'r', encoding='utf-8') as fp:
            po_contents = fp.read()
            found = re.findall(r'^(?P<value>"Plural-Forms.+?\\n")\s*$', po_contents, re.MULTILINE | re.DOTALL)
            self.assertEqual(1, len(found))


class NoWrapExtractorTests(ExtractorTests):

    def test_no_wrap_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0, no_wrap=True)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('This literal should also be included wrapped or not wrapped depending on the use of the --no-wrap option.', po_contents)

    def test_no_wrap_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0, no_wrap=False)
        self.assertTrue(os.path.exists(self.PO_FILE))
        with open(self.PO_FILE, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('""\n"This literal should also be included wrapped or not wrapped depending on the "\n"use of the --no-wrap option."', po_contents, use_quotes=False)


class LocationCommentsTests(ExtractorTests):

    def test_no_location_enabled(self):
        """Behavior is correct if --no-location switch is specified. See #16903."""
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0, no_location=True)
        self.assertTrue(os.path.exists(self.PO_FILE))
        self.assertLocationCommentNotPresent(self.PO_FILE, 55, 'templates', 'test.html.py')

    def test_no_location_disabled(self):
        """Behavior is correct if --no-location switch isn't specified."""
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0, no_location=False)
        self.assertTrue(os.path.exists(self.PO_FILE))
        # #16903 -- Standard comment with source file relative path should be present
        self.assertLocationCommentPresent(self.PO_FILE, 55, 'templates', 'test.html')

        # #21208 -- Leaky paths in comments on Windows e.g. #: path\to\file.html.py:123
        self.assertLocationCommentNotPresent(self.PO_FILE, None, 'templates', 'test.html.py')


class KeepPotFileExtractorTests(ExtractorTests):

    POT_FILE = 'locale/django.pot'

    def setUp(self):
        super(KeepPotFileExtractorTests, self).setUp()

    def tearDown(self):
        super(KeepPotFileExtractorTests, self).tearDown()
        os.chdir(self.test_dir)
        try:
            os.unlink(self.POT_FILE)
        except OSError:
            pass
        os.chdir(self._cwd)

    def test_keep_pot_disabled_by_default(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        self.assertFalse(os.path.exists(self.POT_FILE))

    def test_keep_pot_explicitly_disabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0,
                                keep_pot=False)
        self.assertFalse(os.path.exists(self.POT_FILE))

    def test_keep_pot_enabled(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=[LOCALE], verbosity=0,
                                keep_pot=True)
        self.assertTrue(os.path.exists(self.POT_FILE))


class MultipleLocaleExtractionTests(ExtractorTests):
    PO_FILE_PT = 'locale/pt/LC_MESSAGES/django.po'
    PO_FILE_DE = 'locale/de/LC_MESSAGES/django.po'
    LOCALES = ['pt', 'de', 'ch']

    def tearDown(self):
        os.chdir(self.test_dir)
        for locale in self.LOCALES:
            try:
                self._rmrf('locale/%s' % locale)
            except OSError:
                pass
        os.chdir(self._cwd)

    def test_multiple_locales(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=['pt', 'de'], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_PT))
        self.assertTrue(os.path.exists(self.PO_FILE_DE))


class ExcludedLocaleExtractionTests(ExtractorTests):

    LOCALES = ['en', 'fr', 'it']
    PO_FILE = 'locale/%s/LC_MESSAGES/django.po'

    test_dir = os.path.abspath(os.path.join(this_directory, 'exclude'))

    def _set_times_for_all_po_files(self):
        """
        Set access and modification times to the Unix epoch time for all the .po files.
        """
        for locale in self.LOCALES:
            os.utime(self.PO_FILE % locale, (0, 0))

    def setUp(self):
        super(ExcludedLocaleExtractionTests, self).setUp()

        os.chdir(self.test_dir)  # ExtractorTests.tearDown() takes care of restoring.
        shutil.copytree('canned_locale', 'locale')
        self._set_times_for_all_po_files()
        self.addCleanup(self._rmrf, os.path.join(self.test_dir, 'locale'))

    def test_command_help(self):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = StringIO(), StringIO()
        try:
            # `call_command` bypasses the parser; by calling
            # `execute_from_command_line` with the help subcommand we
            # ensure that there are no issues with the parser itself.
            execute_from_command_line(['django-admin', 'help', 'makemessages'])
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

    def test_one_locale_excluded(self):
        management.call_command('makemessages', exclude=['it'], stdout=StringIO())
        self.assertRecentlyModified(self.PO_FILE % 'en')
        self.assertRecentlyModified(self.PO_FILE % 'fr')
        self.assertNotRecentlyModified(self.PO_FILE % 'it')

    def test_multiple_locales_excluded(self):
        management.call_command('makemessages', exclude=['it', 'fr'], stdout=StringIO())
        self.assertRecentlyModified(self.PO_FILE % 'en')
        self.assertNotRecentlyModified(self.PO_FILE % 'fr')
        self.assertNotRecentlyModified(self.PO_FILE % 'it')

    def test_one_locale_excluded_with_locale(self):
        management.call_command('makemessages', locale=['en', 'fr'], exclude=['fr'], stdout=StringIO())
        self.assertRecentlyModified(self.PO_FILE % 'en')
        self.assertNotRecentlyModified(self.PO_FILE % 'fr')
        self.assertNotRecentlyModified(self.PO_FILE % 'it')

    def test_multiple_locales_excluded_with_locale(self):
        management.call_command('makemessages', locale=['en', 'fr', 'it'], exclude=['fr', 'it'],
                                stdout=StringIO())
        self.assertRecentlyModified(self.PO_FILE % 'en')
        self.assertNotRecentlyModified(self.PO_FILE % 'fr')
        self.assertNotRecentlyModified(self.PO_FILE % 'it')


class CustomLayoutExtractionTests(ExtractorTests):

    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.join(this_directory, 'project_dir')

    def test_no_locale_raises(self):
        os.chdir(self.test_dir)
        with six.assertRaisesRegex(self, management.CommandError,
                "Unable to find a locale path to store translations for file"):
            management.call_command('makemessages', locale=LOCALE, verbosity=0)

    @override_settings(
        LOCALE_PATHS=(os.path.join(
            this_directory, 'project_dir', 'project_locale'),)
    )
    def test_project_locale_paths(self):
        """
        Test that:
          * translations for an app containing a locale folder are stored in that folder
          * translations outside of that app are in LOCALE_PATHS[0]
        """
        os.chdir(self.test_dir)
        self.addCleanup(shutil.rmtree,
            os.path.join(settings.LOCALE_PATHS[0], LOCALE), True)
        self.addCleanup(shutil.rmtree,
            os.path.join(self.test_dir, 'app_with_locale', 'locale', LOCALE), True)

        management.call_command('makemessages', locale=[LOCALE], verbosity=0)
        project_de_locale = os.path.join(
            self.test_dir, 'project_locale', 'de', 'LC_MESSAGES', 'django.po')
        app_de_locale = os.path.join(
            self.test_dir, 'app_with_locale', 'locale', 'de', 'LC_MESSAGES', 'django.po')
        self.assertTrue(os.path.exists(project_de_locale))
        self.assertTrue(os.path.exists(app_de_locale))

        with open(project_de_locale, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('This app has no locale directory', po_contents)
            self.assertMsgId('This is a project-level string', po_contents)
        with open(app_de_locale, 'r') as fp:
            po_contents = force_text(fp.read())
            self.assertMsgId('This app has a locale directory', po_contents)
