"""Runtime regression test for datastar_response: sync handlers must not stall the event loop."""

from __future__ import annotations

import threading
import time
from typing import Any

import anyio
import httpx
import pytest
import uvicorn
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from datastar_py.sse import ServerSentEventGenerator as SSE


@pytest.fixture
def anyio_backend() -> str:
    """Limit anyio plugin to asyncio backend for these tests."""
    return "asyncio"


async def _fetch(
    client: httpx.AsyncClient, path: str, timings: dict[str, float], key: str
) -> None:
    start = time.perf_counter()
    resp = await client.get(path, timeout=5.0)
    timings[key] = time.perf_counter() - start
    resp.raise_for_status()


@pytest.mark.anyio("asyncio")
async def test_sync_handler_runs_off_event_loop() -> None:
    """Sync routes should stay in the threadpool; otherwise they block the event loop."""
    entered = threading.Event()

    from datastar_py.starlette import datastar_response

    @datastar_response
    def slow(request) -> Any:
        entered.set()
        time.sleep(1.0)  # if run on the event loop, this blocks other requests
        return SSE.patch_signals({"slow": True})

    async def ping(request) -> PlainTextResponse:
        return PlainTextResponse("pong")

    app = Starlette(routes=[Route("/slow", slow), Route("/ping", ping)])

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    try:
        # Wait for server to start and expose sockets
        for _ in range(50):
            if server.started and getattr(server, "servers", None):
                break
            await anyio.sleep(0.05)
        else:
            pytest.fail("Server did not start")

        sock = server.servers[0].sockets[0]
        host, port = sock.getsockname()[:2]
        base_url = f"http://{host}:{port}"

        async with httpx.AsyncClient(base_url=base_url) as client:
            timings: dict[str, float] = {}
            async with anyio.create_task_group() as tg:
                tg.start_soon(_fetch, client, "/slow", timings, "slow")
                await anyio.to_thread.run_sync(entered.wait, 1.0)
                tg.start_soon(_fetch, client, "/ping", timings, "ping")

        assert timings["slow"] >= 0.9
        assert timings["ping"] < 0.3, "Ping should not be blocked by slow sync handler"
    finally:
        server.should_exit = True
        thread.join(timeout=2)
