from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from functools import partial, wraps
from inspect import isasyncgenfunction, iscoroutinefunction
from typing import (
    TYPE_CHECKING,
    Any,
    ParamSpec,
)

from litestar.response import Stream

from . import _read_signals
from .sse import SSE_HEADERS, DatastarEvent, DatastarEvents, ServerSentEventGenerator

if TYPE_CHECKING:
    from litestar import Request
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.types import ResponseCookies

__all__ = [
    "SSE_HEADERS",
    "DatastarResponse",
    "ServerSentEventGenerator",
    "read_signals",
]


class DatastarResponse(Stream):
    """Respond with 0..N `DatastarEvent`s."""

    default_headers: dict[str, str] = SSE_HEADERS.copy()

    def __init__(
        self,
        content: DatastarEvents = None,
        *,
        background: BackgroundTask | BackgroundTasks | None = None,
        cookies: ResponseCookies | None = None,
        headers: Mapping[str, str] | None = None,
        status_code: int | None = None,
        # Enables this to be used as a response_class
        **_,  # noqa: ANN003
    ) -> None:
        if not content:
            status_code = status_code or 204
            content = tuple()
        else:
            status_code = status_code or 200
            headers = {**self.default_headers, **(headers or {})}
        if isinstance(content, DatastarEvent):
            content = (content,)
        super().__init__(
            content,
            background=background,
            cookies=cookies,
            headers=headers,
            status_code=status_code,
        )


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
            return DatastarResponse(func(*args, **kwargs))

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


async def read_signals(request: Request) -> dict[str, Any] | None:
    return _read_signals(
        request.method, request.headers, request.query_params, await request.body()
    )
