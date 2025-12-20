from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from functools import partial, wraps
from inspect import isasyncgenfunction, iscoroutinefunction
from typing import Any, ParamSpec

from django.http import HttpRequest
from django.http import StreamingHttpResponse as _StreamingHttpResponse

from . import _read_signals
from .sse import SSE_HEADERS, DatastarEvent, DatastarEvents, ServerSentEventGenerator

__all__ = [
    "SSE_HEADERS",
    "DatastarResponse",
    "ServerSentEventGenerator",
    "read_signals",
]


class DatastarResponse(_StreamingHttpResponse):
    """Respond with 0..N `DatastarEvent`s."""

    default_headers: dict[str, str] = SSE_HEADERS.copy()

    def __init__(
        self,
        content: DatastarEvents = None,
        *,
        status: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if not content:
            status = status or 204
            content = tuple()
        else:
            headers = {**self.default_headers, **(headers or {})}
        if isinstance(content, DatastarEvent):
            content = (content,)
        super().__init__(content, status=status, headers=headers)


P = ParamSpec("P")


def datastar_response(
    func: Callable[P, Awaitable[DatastarEvents] | DatastarEvents],
) -> Callable[P, Awaitable[DatastarResponse] | DatastarResponse]:
    """A decorator which wraps a function result in DatastarResponse.

    Can be used on a sync or async function or generator function.
    Preserves the sync/async nature of the decorated function.
    """
    # Unwrap partials to inspect the actual underlying function
    actual_func = func
    while isinstance(actual_func, partial):
        actual_func = actual_func.func

    # Async generators not supported by Django
    if isasyncgenfunction(actual_func):
        raise NotImplementedError(
            "Async generators are not yet supported by the Django adapter; "
            "use a sync generator or return a single value/awaitable instead."
        )

    # Coroutine (async def + return)
    if iscoroutinefunction(actual_func):

        @wraps(actual_func)
        async def async_coro_wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
            result = await func(*args, **kwargs)
            return DatastarResponse(result)

        async_coro_wrapper.__annotations__["return"] = DatastarResponse
        return async_coro_wrapper

    # Sync Function (def) - includes sync generators
    else:

        @wraps(actual_func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
            return DatastarResponse(func(*args, **kwargs))

        sync_wrapper.__annotations__["return"] = DatastarResponse
        return sync_wrapper


def read_signals(request: HttpRequest) -> dict[str, Any] | None:
    return _read_signals(request.method, request.headers, request.GET, request.body)
