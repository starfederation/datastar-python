from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from functools import wraps
from inspect import isasyncgen, isasyncgenfunction, iscoroutinefunction, isgenerator
from typing import Any, ParamSpec

from quart import Response, copy_current_request_context, request, stream_with_context

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
    # Async generators require stream_with_context wrapping at decoration time
    if isasyncgenfunction(func):

        @wraps(func)
        async def async_gen_wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
            return DatastarResponse(stream_with_context(func)(*args, **kwargs))

        async_gen_wrapper.__annotations__["return"] = DatastarResponse
        return async_gen_wrapper

    if iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
            return DatastarResponse(await copy_current_request_context(func)(*args, **kwargs))

        async_wrapper.__annotations__["return"] = DatastarResponse
        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
        return DatastarResponse(func(*args, **kwargs))

    sync_wrapper.__annotations__["return"] = DatastarResponse
    return sync_wrapper


async def read_signals() -> dict[str, Any] | None:
    return _read_signals(request.method, request.headers, request.args, await request.get_data())
