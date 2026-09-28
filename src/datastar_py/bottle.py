from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import wraps
from typing import Any, ParamSpec

from bottle import HTTPResponse
from bottle import request as _request

from . import _read_signals
from .sse import (
    SSE_HEADERS,
    DatastarEvent,
    DatastarEvents,
    ServerSentEventGenerator,
)

__all__ = [
    "SSE_HEADERS",
    "DatastarResponse",
    "ServerSentEventGenerator",
    "datastar_response",
    "read_signals",
]


class DatastarResponse(HTTPResponse):
    """Respond with 0..N `DatastarEvent`s.

    Bottle natively streams iterable response bodies, so generators are
    passed through unchanged and consumed as they produce events.
    """

    default_headers: dict[str, str] = SSE_HEADERS.copy()

    def __init__(
        self,
        content: DatastarEvents = None,
        *,
        status: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if content is None:
            status = status or 204
            content = ""
            headers = headers or {}
        else:
            status = status or 200
            headers = {**self.default_headers, **(headers or {})}

        if isinstance(content, DatastarEvent):
            content = (content,)

        super().__init__(
            body=content,
            status=status,
            headers=headers,
        )


P = ParamSpec("P")


def datastar_response(
    func: Callable[P, DatastarEvents],
) -> Callable[P, DatastarResponse]:
    """Wrap a route callback's result in a `DatastarResponse`.

    The wrapped function may return a single event, an iterable of events,
    or a generator yielding events.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
        return DatastarResponse(func(*args, **kwargs))

    wrapper.__annotations__["return"] = DatastarResponse
    return wrapper


def read_signals() -> dict[str, Any] | None:
    body = _request.body
    if hasattr(body, "read"):
        body = body.read()

    return _read_signals(
        _request.method,
        _request.headers,
        _request.query,
        body,
    )
