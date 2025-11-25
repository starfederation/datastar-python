from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from functools import wraps
from inspect import isawaitable
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
) -> Callable[P, DatastarResponse]:
    """A decorator which wraps a function result in DatastarResponse.

    Can be used on a sync or async function or generator function.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse:
        r = func(*args, **kwargs)

        if hasattr(r, "__aiter__"):
            return DatastarResponse(r)

        if hasattr(r, "__iter__") and not isinstance(r, (str, bytes)):
            return DatastarResponse(r)

        if isawaitable(r):
            async def await_and_yield():
                yield await r

            return DatastarResponse(await_and_yield())

        return DatastarResponse(r)

    wrapper.__annotations__["return"] = DatastarResponse
    return wrapper


async def read_signals(request: Request) -> dict[str, Any] | None:
    return _read_signals(
        request.method, request.headers, request.query_params, await request.body()
    )
