import re
from django.utils.text import compress_string
from django.utils.cache import patch_vary_headers

re_accepts_gzip = re.compile(r'\bgzip\b')

class GZipMiddleware(object):
    """
    This middleware compresses content if the browser allows gzip compression.
    It sets the Vary header accordingly, so that caches will base their storage
    on the Accept-Encoding header.
    """
    def process_response(self, request, response):
        if response.status_code != 200 or len(response.content) < 200:
            # Not worth compressing really short responses or 304 status
            # responses, etc.
            return response

        patch_vary_headers(response, ('Accept-Encoding',))

        # Avoid gzipping if we've already got a content-encoding or if the
        # content-type is Javascript and the user's browser is IE.
        is_js = ("msie" in request.META.get('HTTP_USER_AGENT', '').lower() and
                "javascript" in response.get('Content-Type', '').lower())
        if response.has_header('Content-Encoding') or is_js:
            return response

        ae = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if not re_accepts_gzip.search(ae):
            return response

        response.content = compress_string(response.content)
        response['Content-Encoding'] = 'gzip'
        response['Content-Length'] = str(len(response.content))
        return response
