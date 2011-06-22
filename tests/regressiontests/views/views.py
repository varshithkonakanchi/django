import sys

from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import get_resolver
from django.shortcuts import render_to_response, render
from django.template import Context, RequestContext, TemplateDoesNotExist
from django.views.debug import technical_500_response, SafeExceptionReporterFilter
from django.views.decorators.debug import (sensitive_post_parameters,
                                           sensitive_variables)
from django.utils.log import getLogger

from regressiontests.views import BrokenException, except_args

from models import Article


def index_page(request):
    """Dummy index page"""
    return HttpResponse('<html><body>Dummy page</body></html>')

def custom_create(request):
    """
    Calls create_object generic view with a custom form class.
    """
    class SlugChangingArticleForm(forms.ModelForm):
        """Custom form class to overwrite the slug."""

        class Meta:
            model = Article

        def save(self, *args, **kwargs):
            self.instance.slug = 'some-other-slug'
            return super(SlugChangingArticleForm, self).save(*args, **kwargs)

    from django.views.generic.create_update import create_object
    return create_object(request,
        post_save_redirect='/create_update/view/article/%(slug)s/',
        form_class=SlugChangingArticleForm)

def raises(request):
    # Make sure that a callable that raises an exception in the stack frame's
    # local vars won't hijack the technical 500 response. See:
    # http://code.djangoproject.com/ticket/15025
    def callable():
        raise Exception
    try:
        raise Exception
    except Exception:
        return technical_500_response(request, *sys.exc_info())

def raises404(request):
    resolver = get_resolver(None)
    resolver.resolve('')

def redirect(request):
    """
    Forces an HTTP redirect.
    """
    return HttpResponseRedirect("target/")

def view_exception(request, n):
    raise BrokenException(except_args[int(n)])

def template_exception(request, n):
    return render_to_response('debug/template_exception.html',
        {'arg': except_args[int(n)]})

# Some views to exercise the shortcuts

def render_to_response_view(request):
    return render_to_response('debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    })

def render_to_response_view_with_request_context(request):
    return render_to_response('debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, context_instance=RequestContext(request))

def render_to_response_view_with_mimetype(request):
    return render_to_response('debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, mimetype='application/x-rendertest')

def render_view(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    })

def render_view_with_base_context(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, context_instance=Context())

def render_view_with_content_type(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, content_type='application/x-rendertest')

def render_view_with_status(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, status=403)

def render_view_with_current_app(request):
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, current_app="foobar_app")

def render_view_with_current_app_conflict(request):
    # This should fail because we don't passing both a current_app and
    # context_instance:
    return render(request, 'debug/render_test.html', {
        'foo': 'FOO',
        'bar': 'BAR',
    }, current_app="foobar_app", context_instance=RequestContext(request))

def raises_template_does_not_exist(request):
    # We need to inspect the HTML generated by the fancy 500 debug view but
    # the test client ignores it, so we send it explicitly.
    try:
        return render_to_response('i_dont_exist.html')
    except TemplateDoesNotExist:
        return technical_500_response(request, *sys.exc_info())

def send_log(request, exc_info):
    logger = getLogger('django.request')
    # The default logging config has a logging filter to ensure admin emails are
    # only sent with DEBUG=False, but since someone might choose to remove that
    # filter, we still want to be able to test the behavior of error emails
    # with DEBUG=True. So we need to remove the filter temporarily.
    admin_email_handler = [
        h for h in logger.handlers
        if h.__class__.__name__ == "AdminEmailHandler"
        ][0]
    orig_filters = admin_email_handler.filters
    admin_email_handler.filters = []
    logger.error('Internal Server Error: %s' % request.path,
        exc_info=exc_info,
        extra={
            'status_code': 500,
            'request': request
        }
    )
    admin_email_handler.filters = orig_filters

def non_sensitive_view(request):
    # Do not just use plain strings for the variables' values in the code
    # so that the tests don't return false positives when the function's source
    # is displayed in the exception report.
    cooked_eggs = ''.join(['s', 'c', 'r', 'a', 'm', 'b', 'l', 'e', 'd'])
    sauce = ''.join(['w', 'o', 'r', 'c', 'e', 's', 't', 'e', 'r', 's', 'h', 'i', 'r', 'e'])
    try:
        raise Exception
    except Exception:
        exc_info = sys.exc_info()
        send_log(request, exc_info)
        return technical_500_response(request, *exc_info)

@sensitive_variables('sauce')
@sensitive_post_parameters('bacon-key', 'sausage-key')
def sensitive_view(request):
    # Do not just use plain strings for the variables' values in the code
    # so that the tests don't return false positives when the function's source
    # is displayed in the exception report.
    cooked_eggs = ''.join(['s', 'c', 'r', 'a', 'm', 'b', 'l', 'e', 'd'])
    sauce = ''.join(['w', 'o', 'r', 'c', 'e', 's', 't', 'e', 'r', 's', 'h', 'i', 'r', 'e'])
    try:
        raise Exception
    except Exception:
        exc_info = sys.exc_info()
        send_log(request, exc_info)
        return technical_500_response(request, *exc_info)

@sensitive_variables()
@sensitive_post_parameters()
def paranoid_view(request):
    # Do not just use plain strings for the variables' values in the code
    # so that the tests don't return false positives when the function's source
    # is displayed in the exception report.
    cooked_eggs = ''.join(['s', 'c', 'r', 'a', 'm', 'b', 'l', 'e', 'd'])
    sauce = ''.join(['w', 'o', 'r', 'c', 'e', 's', 't', 'e', 'r', 's', 'h', 'i', 'r', 'e'])
    try:
        raise Exception
    except Exception:
        exc_info = sys.exc_info()
        send_log(request, exc_info)
        return technical_500_response(request, *exc_info)

class UnsafeExceptionReporterFilter(SafeExceptionReporterFilter):
    """
    Ignores all the filtering done by its parent class.
    """

    def get_post_parameters(self, request):
        return request.POST

    def get_traceback_frame_variables(self, request, tb_frame):
        return tb_frame.f_locals.items()


@sensitive_variables()
@sensitive_post_parameters()
def custom_exception_reporter_filter_view(request):
    # Do not just use plain strings for the variables' values in the code
    # so that the tests don't return false positives when the function's source
    # is displayed in the exception report.
    cooked_eggs = ''.join(['s', 'c', 'r', 'a', 'm', 'b', 'l', 'e', 'd'])
    sauce = ''.join(['w', 'o', 'r', 'c', 'e', 's', 't', 'e', 'r', 's', 'h', 'i', 'r', 'e'])
    request.exception_reporter_filter = UnsafeExceptionReporterFilter()
    try:
        raise Exception
    except Exception:
        exc_info = sys.exc_info()
        send_log(request, exc_info)
        return technical_500_response(request, *exc_info)
