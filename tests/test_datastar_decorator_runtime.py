"""Runtime-focused tests for datastar_response decorators."""

from __future__ import annotations

import importlib
import inspect
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


@pytest.mark.parametrize("module_path", ["datastar_py.starlette", "datastar_py.fasthtml"])
@pytest.mark.parametrize(
    "variant",
    [
        "sync_value",
        "sync_generator",
        "async_value",
        "async_generator",
    ],
)
def test_decorator_preserves_sync_async_semantics(module_path: str, variant: str) -> None:
    """Decorated handlers should preserve sync/async nature of the original function."""

    mod = importlib.import_module(module_path)
    datastar_response = mod.datastar_response
    DatastarResponse = mod.DatastarResponse

    if variant == "sync_value":
        @datastar_response
        def handler() -> Any:
            return SSE.patch_signals({"ok": True})
    elif variant == "sync_generator":
        @datastar_response
        def handler() -> Any:
            yield SSE.patch_signals({"ok": True})
    elif variant == "async_value":
        @datastar_response
        async def handler() -> Any:
            return SSE.patch_signals({"ok": True})
    else:
        @datastar_response
        async def handler() -> Any:
            yield SSE.patch_signals({"ok": True})

    is_async_variant = variant.startswith("async_")

    # Verify the wrapper preserves sync/async nature
    if is_async_variant:
        assert inspect.iscoroutinefunction(handler), "Async handlers should remain async"
        # Call and close coroutine to avoid warnings (we can't await in sync test)
        coro = handler()
        coro.close()
    else:
        assert not inspect.iscoroutinefunction(handler), "Sync handlers should remain sync"
        result = handler()
        assert isinstance(result, DatastarResponse), "Sync handlers should return DatastarResponse directly"


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
    def slow(request) -> Any:  # noqa: ANN001
        entered.set()
        time.sleep(1.0)  # if run on the event loop, this blocks other requests
        return SSE.patch_signals({"slow": True})

    async def ping(request) -> PlainTextResponse:  # noqa: ANN001
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


def test_async_generator_iterates_on_event_loop() -> None:
    """Async generators should iterate on the event loop, not spawn a thread.

    The decorator preserves async nature: async generators get an async wrapper,
    ensuring they run on the event loop. Sync generators get a sync wrapper,
    running in the threadpool. This test verifies these execute in different
    thread contexts as expected.
    """
    from starlette.testclient import TestClient

    from datastar_py.starlette import datastar_response

    execution_threads: dict[str, str] = {}

    @datastar_response
    async def async_gen_handler(request) -> Any:  # noqa: ANN001
        execution_threads["async_gen"] = threading.current_thread().name
        yield SSE.patch_signals({"async": True})

    @datastar_response
    def sync_gen_handler(request) -> Any:  # noqa: ANN001
        execution_threads["sync_gen"] = threading.current_thread().name
        yield SSE.patch_signals({"sync": True})

    app = Starlette(routes=[
        Route("/async", async_gen_handler),
        Route("/sync", sync_gen_handler),
    ])

    with TestClient(app) as client:
        client.get("/async")
        client.get("/sync")

    # Async generator runs on the asyncio portal thread (event loop context)
    # Sync generator runs in a separate threadpool worker
    # The key assertion: they run in DIFFERENT thread contexts
    assert execution_threads["async_gen"] != execution_threads["sync_gen"], (
        f"Async and sync generators should run in different thread contexts. "
        f"Async ran on: {execution_threads['async_gen']}, Sync ran on: {execution_threads['sync_gen']}"
    )

    # Async generator should be on the event loop thread (asyncio-portal-* or MainThread)
    assert "asyncio" in execution_threads["async_gen"] or execution_threads["async_gen"] == "MainThread", (
        f"Async generator should run on event loop, but ran on {execution_threads['async_gen']}"
    )
