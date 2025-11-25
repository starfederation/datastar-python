"""Integration test: datastar_response within a live FastAPI app."""

from __future__ import annotations

import threading
import time
from typing import Any

import anyio
import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from starlette.responses import PlainTextResponse

from datastar_py.sse import ServerSentEventGenerator as SSE
from datastar_py.fastapi import datastar_response


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def _fetch(client: httpx.AsyncClient, path: str) -> httpx.Response:
    resp = await client.get(path, timeout=5.0)
    resp.raise_for_status()
    return resp


@pytest.mark.anyio
async def test_fastapi_handlers_cover_matrix() -> None:
    """Ensure FastAPI handlers across sync/async and gen/value work end-to-end."""

    entered = threading.Event()
    app = FastAPI()

    @app.get("/sync-value")
    @datastar_response
    def sync_value() -> Any:
        entered.set()
        time.sleep(0.2)  # should run in threadpool
        return SSE.patch_signals({"src": "sync_value"})

    @app.get("/sync-generator")
    @datastar_response
    def sync_gen() -> Any:
        yield SSE.patch_signals({"src": "sync_generator", "idx": 1})
        yield SSE.patch_signals({"src": "sync_generator", "idx": 2})

    @app.get("/async-value")
    @datastar_response
    async def async_value() -> Any:
        return SSE.patch_signals({"src": "async_value"})

    @app.get("/async-generator")
    @datastar_response
    async def async_gen() -> Any:
        yield SSE.patch_signals({"src": "async_generator", "idx": 1})
        yield SSE.patch_signals({"src": "async_generator", "idx": 2})

    @app.get("/ping")
    async def ping() -> PlainTextResponse:
        return PlainTextResponse("pong")

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
            # Concurrency sanity: sync_value should not stall ping
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
