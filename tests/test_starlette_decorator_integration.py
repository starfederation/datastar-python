"""Integration test: datastar_response within a live Starlette app."""

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
from datastar_py.starlette import datastar_response


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _fetch(client: httpx.AsyncClient, path: str) -> httpx.Response:
    resp = await client.get(path, timeout=5.0)
    resp.raise_for_status()
    return resp


@pytest.mark.anyio
async def test_starlette_sync_handler_runs_in_threadpool_and_streams() -> None:
    """Ensure all handler shapes work end-to-end and sync stays in threadpool."""

    entered = threading.Event()

    @datastar_response
    def sync_value(request) -> Any:  # noqa: ANN001
        entered.set()
        time.sleep(0.2)  # should not block event loop
        return SSE.patch_signals({"src": "sync_value"})

    @datastar_response
    def sync_gen(request) -> Any:  # noqa: ANN001
        yield SSE.patch_signals({"src": "sync_generator", "idx": 1})
        yield SSE.patch_signals({"src": "sync_generator", "idx": 2})

    @datastar_response
    async def async_value(request) -> Any:  # noqa: ANN001
        return SSE.patch_signals({"src": "async_value"})

    @datastar_response
    async def async_gen(request) -> Any:  # noqa: ANN001
        yield SSE.patch_signals({"src": "async_generator", "idx": 1})
        yield SSE.patch_signals({"src": "async_generator", "idx": 2})

    async def ping(request) -> PlainTextResponse:  # noqa: ANN001
        return PlainTextResponse("pong")

    app = Starlette(
        routes=[
            Route("/sync-value", sync_value),
            Route("/sync-generator", sync_gen),
            Route("/async-value", async_value),
            Route("/async-generator", async_gen),
            Route("/ping", ping),
        ]
    )

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    try:
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
            # Verify blocking sync handler doesn't stall other requests
            # Concurrency sanity: sync_value blocks 0.2s but should not stall ping
            async with anyio.create_task_group() as tg:
                slow_resp: httpx.Response | None = None
                ping_resp: httpx.Response | None = None

                async def hit_slow():
                    nonlocal slow_resp
                    slow_resp = await _fetch(client, "/sync-value")

                async def hit_ping():
                    nonlocal ping_resp
                    await anyio.to_thread.run_sync(entered.wait, 1.0)
                    ping_resp = await _fetch(client, "/ping")

                tg.start_soon(hit_slow)
                tg.start_soon(hit_ping)

            assert slow_resp is not None and slow_resp.status_code == 200
            assert ping_resp is not None and ping_resp.status_code == 200
            assert float(ping_resp.elapsed.total_seconds()) < 0.35

            # Verify content of each endpoint
            sync_value_body = (await _fetch(client, "/sync-value")).text
            assert '"src":"sync_value"' in sync_value_body

            sync_gen_body = (await _fetch(client, "/sync-generator")).text
            assert '"src":"sync_generator"' in sync_gen_body
            assert '"idx":1' in sync_gen_body and '"idx":2' in sync_gen_body

            async_value_body = (await _fetch(client, "/async-value")).text
            assert '"src":"async_value"' in async_value_body

            async_gen_body = (await _fetch(client, "/async-generator")).text
            assert '"src":"async_generator"' in async_gen_body
            assert '"idx":1' in async_gen_body and '"idx":2' in async_gen_body
    finally:
        server.should_exit = True
        thread.join(timeout=2)
