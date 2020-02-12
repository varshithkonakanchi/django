import asyncio
from http import HTTPStatus

from django.core.exceptions import SuspiciousOperation
from django.db import connection, transaction
from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt


def regular(request):
    return HttpResponse(b"regular content")


def no_response(request):
    pass


class NoResponse:
    def __call__(self, request):
        pass


def streaming(request):
    return StreamingHttpResponse([b"streaming", b" ", b"content"])


def in_transaction(request):
    return HttpResponse(str(connection.in_atomic_block))


@transaction.non_atomic_requests
def not_in_transaction(request):
    return HttpResponse(str(connection.in_atomic_block))


def suspicious(request):
    raise SuspiciousOperation('dubious')


@csrf_exempt
def malformed_post(request):
    request.POST
    return HttpResponse()


def httpstatus_enum(request):
    return HttpResponse(status=HTTPStatus.OK)


async def async_regular(request):
    return HttpResponse(b'regular content')


async def async_unawaited(request):
    """Return an unawaited coroutine (common error for async views)."""
    return asyncio.sleep(0)
