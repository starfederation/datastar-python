from collections.abc import Callable, Coroutine
from typing import Any, reveal_type

from django.http import HttpRequest
from django.urls import path

from datastar_py.django import DatastarResponse, datastar_response
from datastar_py.sse import AsyncDatastarEvents, SyncDatastarEvents
from datastar_py.sse import ServerSentEventGenerator as SSE


@datastar_response
def sync_view(request: HttpRequest) -> SyncDatastarEvents:
    return SSE.patch_elements('<div id="sync"></div>')


@datastar_response
async def async_coro_view(request: HttpRequest) -> SyncDatastarEvents:
    return SSE.patch_elements('<div id="coro"></div>')


@datastar_response
async def async_gen_view(request: HttpRequest) -> AsyncDatastarEvents:
    yield SSE.patch_elements('<div id="gen"></div>')


sync_typed: Callable[[HttpRequest], DatastarResponse] = sync_view
async_coro_typed: Callable[[HttpRequest], Coroutine[Any, Any, DatastarResponse]] = async_coro_view
async_gen_typed: Callable[[HttpRequest], Coroutine[Any, Any, DatastarResponse]] = async_gen_view

reveal_type(sync_view)
reveal_type(async_coro_view)
reveal_type(async_gen_view)

urlpatterns = [
    path("sync/", sync_view),
    path("coro/", async_coro_view),
    path("gen/", async_gen_view),
]
