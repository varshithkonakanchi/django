import os
from Cookie import SimpleCookie
from pprint import pformat
from urllib import urlencode
from django.utils.datastructures import MultiValueDict, FileDict
from django.utils.encoding import smart_str, iri_to_uri, force_unicode

RESERVED_CHARS="!*'();:@&=+$,/?%#[]"

try:
    # The mod_python version is more efficient, so try importing it first.
    from mod_python.util import parse_qsl
except ImportError:
    from cgi import parse_qsl

class Http404(Exception):
    pass

class HttpRequest(object):
    "A basic HTTP request"

    # The encoding used in GET/POST dicts. None means use default setting.
    _encoding = None

    def __init__(self):
        self.GET, self.POST, self.COOKIES, self.META, self.FILES = {}, {}, {}, {}, {}
        self.path = ''
        self.method = None

    def __repr__(self):
        return '<HttpRequest\nGET:%s,\nPOST:%s,\nCOOKIES:%s,\nMETA:%s>' % \
            (pformat(self.GET), pformat(self.POST), pformat(self.COOKIES),
            pformat(self.META))

    def __getitem__(self, key):
        for d in (self.POST, self.GET):
            if key in d:
                return d[key]
        raise KeyError, "%s not found in either POST or GET" % key

    def has_key(self, key):
        return key in self.GET or key in self.POST

    def get_full_path(self):
        return ''

    def is_secure(self):
        return os.environ.get("HTTPS") == "on"

    def _set_encoding(self, val):
        """
        Sets the encoding used for GET/POST accesses. If the GET or POST
        dictionary has already been created, it is removed and recreated on the
        next access (so that it is decoded correctly).
        """
        self._encoding = val
        if hasattr(self, '_get'):
            del self._get
        if hasattr(self, '_post'):
            del self._post

    def _get_encoding(self):
        return self._encoding

    encoding = property(_get_encoding, _set_encoding)

def parse_file_upload(header_dict, post_data):
    "Returns a tuple of (POST QueryDict, FILES MultiValueDict)"
    import email, email.Message
    from cgi import parse_header
    raw_message = '\r\n'.join(['%s:%s' % pair for pair in header_dict.items()])
    raw_message += '\r\n\r\n' + post_data
    msg = email.message_from_string(raw_message)
    POST = QueryDict('', mutable=True)
    FILES = MultiValueDict()
    for submessage in msg.get_payload():
        if submessage and isinstance(submessage, email.Message.Message):
            name_dict = parse_header(submessage['Content-Disposition'])[1]
            # name_dict is something like {'name': 'file', 'filename': 'test.txt'} for file uploads
            # or {'name': 'blah'} for POST fields
            # We assume all uploaded files have a 'filename' set.
            if 'filename' in name_dict:
                assert type([]) != type(submessage.get_payload()), "Nested MIME messages are not supported"
                if not name_dict['filename'].strip():
                    continue
                # IE submits the full path, so trim everything but the basename.
                # (We can't use os.path.basename because that uses the server's
                # directory separator, which may not be the same as the
                # client's one.)
                filename = name_dict['filename'][name_dict['filename'].rfind("\\")+1:]
                FILES.appendlist(name_dict['name'], FileDict({
                    'filename': filename,
                    'content-type': 'Content-Type' in submessage and submessage['Content-Type'] or None,
                    'content': submessage.get_payload(),
                }))
            else:
                POST.appendlist(name_dict['name'], submessage.get_payload())
    return POST, FILES

class QueryDict(MultiValueDict):
    """
    A specialized MultiValueDict that takes a query string when initialized.
    This is immutable unless you create a copy of it.

    Values retrieved from this class are converted from the given encoding
    (DEFAULT_CHARSET by default) to unicode.
    """
    def __init__(self, query_string, mutable=False, encoding=None):
        MultiValueDict.__init__(self)
        if not encoding:
            # *Important*: do not import settings any earlier because of note
            # in core.handlers.modpython.
            from django.conf import settings
            encoding = settings.DEFAULT_CHARSET
        self.encoding = encoding
        self._mutable = True
        for key, value in parse_qsl((query_string or ''), True): # keep_blank_values=True
            self.appendlist(force_unicode(key, encoding, errors='replace'), force_unicode(value, encoding, errors='replace'))
        self._mutable = mutable

    def _assert_mutable(self):
        if not self._mutable:
            raise AttributeError, "This QueryDict instance is immutable"

    def __setitem__(self, key, value):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        value = str_to_unicode(value, self.encoding)
        MultiValueDict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self._assert_mutable()
        super(QueryDict, self).__delitem__(key)

    def __copy__(self):
        result = self.__class__('', mutable=True)
        for key, value in dict.items(self):
            dict.__setitem__(result, key, value)
        return result

    def __deepcopy__(self, memo={}):
        import copy
        result = self.__class__('', mutable=True)
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def setlist(self, key, list_):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        list_ = [str_to_unicode(elt, self.encoding) for elt in list_]
        MultiValueDict.setlist(self, key, list_)

    def setlistdefault(self, key, default_list=()):
        self._assert_mutable()
        if key not in self:
            self.setlist(key, default_list)
        return MultiValueDict.getlist(self, key)

    def appendlist(self, key, value):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        value = str_to_unicode(value, self.encoding)
        MultiValueDict.appendlist(self, key, value)

    def update(self, other_dict):
        self._assert_mutable()
        f = lambda s: str_to_unicode(s, self.encoding)
        d = dict([(f(k), f(v)) for k, v in other_dict.items()])
        MultiValueDict.update(self, d)

    def pop(self, key, *args):
        self._assert_mutable()
        return MultiValueDict.pop(self, key, *args)

    def popitem(self):
        self._assert_mutable()
        return MultiValueDict.popitem(self)

    def clear(self):
        self._assert_mutable()
        MultiValueDict.clear(self)

    def setdefault(self, key, default=None):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        default = str_to_unicode(default, self.encoding)
        return MultiValueDict.setdefault(self, key, default)

    def copy(self):
        "Returns a mutable copy of this object."
        return self.__deepcopy__()

    def urlencode(self):
        output = []
        for k, list_ in self.lists():
            k = smart_str(k, self.encoding)
            output.extend([urlencode({k: smart_str(v, self.encoding)}) for v in list_])
        return '&'.join(output)

def parse_cookie(cookie):
    if cookie == '':
        return {}
    c = SimpleCookie()
    c.load(cookie)
    cookiedict = {}
    for key in c.keys():
        cookiedict[key] = c.get(key).value
    return cookiedict

class HttpResponse(object):
    "A basic HTTP response, with content and dictionary-accessed headers"

    status_code = 200

    def __init__(self, content='', mimetype=None, status=None,
            content_type=None):
        from django.conf import settings
        self._charset = settings.DEFAULT_CHARSET
        if mimetype:
            content_type = mimetype     # For backwards compatibility
        if not content_type:
            content_type = "%s; charset=%s" % (settings.DEFAULT_CONTENT_TYPE,
                    settings.DEFAULT_CHARSET)
        if not isinstance(content, basestring) and hasattr(content, '__iter__'):
            self._container = content
            self._is_string = False
        else:
            self._container = [content]
            self._is_string = True
        self.headers = {'Content-Type': content_type}
        self.cookies = SimpleCookie()
        if status:
            self.status_code = status

    def __str__(self):
        "Full HTTP message, including headers"
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self.headers.items()]) \
            + '\n\n' + self.content

    def __setitem__(self, header, value):
        self.headers[header] = value

    def __delitem__(self, header):
        try:
            del self.headers[header]
        except KeyError:
            pass

    def __getitem__(self, header):
        return self.headers[header]

    def has_header(self, header):
        "Case-insensitive check for a header"
        header = header.lower()
        for key in self.headers.keys():
            if key.lower() == header:
                return True
        return False

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/', domain=None, secure=None):
        self.cookies[key] = value
        for var in ('max_age', 'path', 'domain', 'secure', 'expires'):
            val = locals()[var]
            if val is not None:
                self.cookies[key][var.replace('_', '-')] = val

    def delete_cookie(self, key, path='/', domain=None):
        self.cookies[key] = ''
        if path is not None:
            self.cookies[key]['path'] = path
        if domain is not None:
            self.cookies[key]['domain'] = domain
        self.cookies[key]['expires'] = 0
        self.cookies[key]['max-age'] = 0

    def _get_content(self):
        content = smart_str(''.join(self._container), self._charset)
        return content

    def _set_content(self, value):
        self._container = [value]
        self._is_string = True

    content = property(_get_content, _set_content)

    def __iter__(self):
        self._iterator = self._container.__iter__()
        return self

    def next(self):
        chunk = self._iterator.next()
        if isinstance(chunk, unicode):
            chunk = chunk.encode(self._charset)
        return chunk

    def close(self):
        if hasattr(self._container, 'close'):
            self._container.close()

    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        if not self._is_string:
            raise Exception, "This %s instance is not writable" % self.__class__
        self._container.append(content)

    def flush(self):
        pass

    def tell(self):
        if not self._is_string:
            raise Exception, "This %s instance cannot tell its position" % self.__class__
        return sum([len(chunk) for chunk in self._container])

class HttpResponseRedirect(HttpResponse):
    status_code = 302

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)

class HttpResponsePermanentRedirect(HttpResponse):
    status_code = 301

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)

class HttpResponseNotModified(HttpResponse):
    status_code = 304

class HttpResponseBadRequest(HttpResponse):
    status_code = 400

class HttpResponseNotFound(HttpResponse):
    status_code = 404

class HttpResponseForbidden(HttpResponse):
    status_code = 403

class HttpResponseNotAllowed(HttpResponse):
    status_code = 405

    def __init__(self, permitted_methods):
        HttpResponse.__init__(self)
        self['Allow'] = ', '.join(permitted_methods)

class HttpResponseGone(HttpResponse):
    status_code = 410

    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)

class HttpResponseServerError(HttpResponse):
    status_code = 500

    def __init__(self, *args, **kwargs):
        HttpResponse.__init__(self, *args, **kwargs)

def get_host(request):
    "Gets the HTTP host from the environment or request headers."
    host = request.META.get('HTTP_X_FORWARDED_HOST', '')
    if not host:
        host = request.META.get('HTTP_HOST', '')
    return host

# It's neither necessary nor appropriate to use
# django.utils.encoding.smart_unicode for parsing URLs and form inputs. Thus,
# this slightly more restricted function.
def str_to_unicode(s, encoding):
    """
    Convert basestring objects to unicode, using the given encoding. Illegaly
    encoded input characters are replaced with Unicode "unknown" codepoint
    (\ufffd).

    Returns any non-basestring objects without change.
    """
    if isinstance(s, str):
        return unicode(s, encoding, 'replace')
    else:
        return s

