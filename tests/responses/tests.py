# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import io

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.http.response import HttpResponseBase
from django.test import SimpleTestCase

UTF8 = 'utf-8'
ISO88591 = 'iso-8859-1'


class HttpResponseBaseTests(SimpleTestCase):
    def test_closed(self):
        r = HttpResponseBase()
        self.assertIs(r.closed, False)

        r.close()
        self.assertIs(r.closed, True)

    def test_write(self):
        r = HttpResponseBase()
        self.assertIs(r.writable(), False)

        with self.assertRaisesMessage(IOError, 'This HttpResponseBase instance is not writable'):
            r.write('asdf')
        with self.assertRaisesMessage(IOError, 'This HttpResponseBase instance is not writable'):
            r.writelines(['asdf\n', 'qwer\n'])

    def test_tell(self):
        r = HttpResponseBase()
        with self.assertRaisesMessage(IOError, 'This HttpResponseBase instance cannot tell its position'):
            r.tell()

    def test_setdefault(self):
        """
        HttpResponseBase.setdefault() should not change an existing header
        and should be case insensitive.
        """
        r = HttpResponseBase()

        r['Header'] = 'Value'
        r.setdefault('header', 'changed')
        self.assertEqual(r['header'], 'Value')

        r.setdefault('x-header', 'DefaultValue')
        self.assertEqual(r['X-Header'], 'DefaultValue')


class HttpResponseTests(SimpleTestCase):
    def test_status_code(self):
        resp = HttpResponse(status=503)
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.reason_phrase, "Service Unavailable")

    def test_change_status_code(self):
        resp = HttpResponse()
        resp.status_code = 503
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.reason_phrase, "Service Unavailable")

    def test_reason_phrase(self):
        reason = "I'm an anarchist coffee pot on crack."
        resp = HttpResponse(status=814, reason=reason)
        self.assertEqual(resp.status_code, 814)
        self.assertEqual(resp.reason_phrase, reason)

    def test_charset_detection(self):
        """ HttpResponse should parse charset from content_type."""
        response = HttpResponse('ok')
        self.assertEqual(response.charset, settings.DEFAULT_CHARSET)

        response = HttpResponse(charset=ISO88591)
        self.assertEqual(response.charset, ISO88591)
        self.assertEqual(response['Content-Type'], 'text/html; charset=%s' % ISO88591)

        response = HttpResponse(content_type='text/plain; charset=%s' % UTF8, charset=ISO88591)
        self.assertEqual(response.charset, ISO88591)

        response = HttpResponse(content_type='text/plain; charset=%s' % ISO88591)
        self.assertEqual(response.charset, ISO88591)

        response = HttpResponse(content_type='text/plain; charset="%s"' % ISO88591)
        self.assertEqual(response.charset, ISO88591)

        response = HttpResponse(content_type='text/plain; charset=')
        self.assertEqual(response.charset, settings.DEFAULT_CHARSET)

        response = HttpResponse(content_type='text/plain')
        self.assertEqual(response.charset, settings.DEFAULT_CHARSET)

    def test_response_content_charset(self):
        """HttpResponse should encode based on charset."""
        content = "Café :)"
        utf8_content = content.encode(UTF8)
        iso_content = content.encode(ISO88591)

        response = HttpResponse(utf8_content)
        self.assertContains(response, utf8_content)

        response = HttpResponse(iso_content, content_type='text/plain; charset=%s' % ISO88591)
        self.assertContains(response, iso_content)

        response = HttpResponse(iso_content)
        self.assertContains(response, iso_content)

        response = HttpResponse(iso_content, content_type='text/plain')
        self.assertContains(response, iso_content)

    def test_repr(self):
        response = HttpResponse(content="Café :)".encode(UTF8), status=201)
        expected = '<HttpResponse status_code=201, "text/html; charset=utf-8">'
        self.assertEqual(repr(response), expected)

    def test_wrap_textiowrapper(self):
        content = "Café :)"
        r = HttpResponse()
        with io.TextIOWrapper(r, UTF8) as buf:
            buf.write(content)
        self.assertEqual(r.content, content.encode(UTF8))

    def test_generator_cache(self):
        generator = ("{}".format(i) for i in range(10))
        response = HttpResponse(content=generator)
        self.assertEqual(response.content, b'0123456789')
        self.assertRaises(StopIteration, next, generator)

        cache.set('my-response-key', response)
        response = cache.get('my-response-key')
        self.assertEqual(response.content, b'0123456789')
