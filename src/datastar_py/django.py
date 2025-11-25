from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from functools import wraps
from inspect import isawaitable
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
) -> Callable[P, Awaitable[DatastarResponse]]:
    """A decorator which wraps a function result in DatastarResponse.

    Can be used on a sync or async function or generator function.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
        r = func(*args, **kwargs)

        if hasattr(r, "__aiter__"):
            raise NotImplementedError(
                "Async generators/iterables are not yet supported by the Django adapter; "
                "use a sync generator or return a single value/awaitable instead."
            )

        if hasattr(r, "__iter__") and not isinstance(r, (str, bytes)):
            return DatastarResponse(r)

        if isawaitable(r):
            return DatastarResponse(await r)
        return DatastarResponse(r)

    return wrapper


def read_signals(request: HttpRequest) -> dict[str, Any] | None:
    return _read_signals(request.method, request.headers, request.GET, request.body)
