from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from functools import partial, wraps
from inspect import isasyncgen, isasyncgenfunction, iscoroutinefunction, isgenerator
from typing import Any, ParamSpec

from quart import Response, request, stream_with_context

from . import _read_signals
from .sse import SSE_HEADERS, DatastarEvents, ServerSentEventGenerator

__all__ = [
    "SSE_HEADERS",
    "DatastarResponse",
    "ServerSentEventGenerator",
    "read_signals",
]


class DatastarResponse(Response):
    """Respond with 0..N `DatastarEvent`s."""

    default_headers: dict[str, str] = SSE_HEADERS.copy()

    def __init__(
        self,
        content: DatastarEvents = None,
        status: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if not content:
            status = status or 204
        else:
            headers = {**self.default_headers, **(headers or {})}
        super().__init__(content, status=status, headers=headers)
        if isgenerator(content) or isasyncgen(content):
            self.timeout = None


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

    # Case A: Async Generator (async def + yield)
    if isasyncgenfunction(actual_func):

        @wraps(actual_func)
        async def async_gen_wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
            return DatastarResponse(stream_with_context(func)(*args, **kwargs))

        async_gen_wrapper.__annotations__["return"] = DatastarResponse
        return async_gen_wrapper

    # Case B: Standard Coroutine (async def + return)
    elif iscoroutinefunction(actual_func):

        @wraps(actual_func)
        async def async_coro_wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
            result = await func(*args, **kwargs)
            return DatastarResponse(result)

        async_coro_wrapper.__annotations__["return"] = DatastarResponse
        return async_coro_wrapper

    # Case C: Sync Function (def) - includes sync generators
    else:

        @wraps(actual_func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
            return DatastarResponse(func(*args, **kwargs))

        sync_wrapper.__annotations__["return"] = DatastarResponse
        return sync_wrapper


async def read_signals() -> dict[str, Any] | None:
    return _read_signals(request.method, request.headers, request.args, await request.get_data())
