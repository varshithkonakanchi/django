from django.http import HttpResponse
from django.utils.decorators import decorator_from_middleware
from django.middleware.doc import XViewMiddleware


xview_dec = decorator_from_middleware(XViewMiddleware)

def xview(request):
    return HttpResponse()
xview = xview_dec(xview)
