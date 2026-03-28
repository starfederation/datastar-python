from __future__ import annotations

from collections.abc import Awaitable, Callable, Collection, Mapping
from contextlib import aclosing, closing
from functools import wraps
from inspect import isasyncgen, isgenerator
from typing import Any, ParamSpec

from sanic import HTTPResponse, Request

try:
    import brotli

    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False

from . import _read_signals
from .sse import SSE_HEADERS, DatastarEvent, DatastarEvents, ServerSentEventGenerator

__all__ = [
    "SSE_HEADERS",
    "DatastarResponse",
    "ServerSentEventGenerator",
    "datastar_respond",
    "read_signals",
]


class DatastarResponse(HTTPResponse):
    default_headers: dict[str, str] = SSE_HEADERS.copy()

    def __init__(
        self,
        content: DatastarEvent | Collection[DatastarEvent] | None = None,
        status: int | None = None,
        headers: Mapping[str, str] | None = None,
        compression: bool = False,
        brotli_quality: int | None = None,
        brotli_lgwin: int | None = None,
    ) -> None:
        self._compression = compression
        self._brotli_compressor = None
        self._brotli_quality = brotli_quality if brotli_quality is not None else 11
        self._brotli_lgwin = brotli_lgwin if brotli_lgwin is not None else 22

        if not content:
            status = status or 204
        elif not isinstance(content, str):
            # Collections of events just get concatenated
            content = "".join(content)
        super().__init__(
            content, status=status or 200, headers={**self.default_headers, **(headers or {})}
        )

    async def send(
        self,
        event: DatastarEvent | None = None,
        end_stream: bool | None = None,
    ) -> None:
        if event and self.status == 204:
            # When the response is created with no content, it's set to a 204 by default
            # if we end up streaming to it, change the status code to 200 before sending.
            self.status = 200
        if not event and end_stream is None:
            end_stream = True
        data = event.encode("utf-8") if event else b""
        if self._compression:
            if not BROTLI_AVAILABLE:
                raise ImportError("brotli is not installed")
            if self._brotli_compressor is None and data:
                self._brotli_compressor = brotli.Compressor(
                    mode=brotli.MODE_TEXT,
                    quality=self._brotli_quality,
                    lgwin=self._brotli_lgwin,
                )
                self.headers["Content-Encoding"] = "br"
            if data:
                data = self._brotli_compressor.process(data)
                data += self._brotli_compressor.flush()
            if end_stream and self._brotli_compressor:
                data += self._brotli_compressor.finish()
        await super().send(data, end_stream=end_stream)


async def datastar_respond(
    request: Request,
    *,
    status: int = 200,
    headers: Mapping[str, str] | None = None,
    compression: bool = False,
    brotli_quality: int | None = None,
    brotli_lgwin: int | None = None,
) -> DatastarResponse:
    return await request.respond(
        DatastarResponse(
            status=status,
            headers=headers,
            compression=compression and _client_accepts_brotli(request),
            brotli_quality=brotli_quality,
            brotli_lgwin=brotli_lgwin,
        )
    )


P = ParamSpec("P")


def datastar_response(
    func: Callable[P, Awaitable[DatastarEvents] | DatastarEvents],
) -> Callable[P, Awaitable[DatastarResponse | None]]:
    """A decorator which wraps a function result in DatastarResponse.

    Can be used on a sync or async function or generator function.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> DatastarResponse | None:
        r = func(*args, **kwargs)
        if isinstance(r, Awaitable):
            return DatastarResponse(await r)
        if isasyncgen(r):
            request = args[0]
            response = await request.respond(response=DatastarResponse())
            # Make sure when the client cancels the stream clean up the generator now
            # Without the aclosing manager it would happen at garbage collection
            async with aclosing(r) as ait:
                async for event in ait:
                    await response.send(event)
            await response.eof()
            return None
        if isgenerator(r):
            request = args[0]
            response = await request.respond(response=DatastarResponse())
            with closing(r) as it:
                for event in it:
                    await response.send(event)
            await response.eof()
            return None
        return DatastarResponse(r)

    wrapper.__annotations__["return"] = DatastarResponse | None
    return wrapper


async def read_signals(request: Request) -> dict[str, Any] | None:
    return _read_signals(request.method, request.headers, request.args, request.body)


def _client_accepts_brotli(request: Request) -> bool:
    """Return True if the client's Accept-Encoding includes brotli."""
    accept_encoding = request.headers.get("Accept-Encoding", "")
    return any(part.split(";")[0].strip() == "br" for part in accept_encoding.split(","))
