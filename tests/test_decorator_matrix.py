"""Matrix tests for datastar_response across frameworks and callable types."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Iterable
from typing import Any

import pytest

from datastar_py.sse import ServerSentEventGenerator as SSE

FRAMEWORKS = [
    # name, module path, iterator attribute on response (None means use response directly)
    ("starlette", "datastar_py.starlette", "body_iterator"),
    ("fasthtml", "datastar_py.fasthtml", "body_iterator"),
    ("fastapi", "datastar_py.fastapi", "body_iterator"),
    ("litestar", "datastar_py.litestar", "iterator"),
    ("django", "datastar_py.django", None),
    # Quart and Sanic need full request contexts; covered elsewhere
    ("quart", "datastar_py.quart", None),
    ("sanic", "datastar_py.sanic", None),
]


@pytest.fixture
def anyio_backend() -> str:
    """Limit anyio plugin to asyncio backend for these tests."""
    return "asyncio"


def _require_module(module_path: str) -> Any:
    if not importlib.util.find_spec(module_path):
        pytest.skip(f"{module_path} not installed")
    return importlib.import_module(module_path)


async def _collect_events(resp: Any, iterator_attr: str | None) -> list[Any]:
    """Gather events from response regardless of iterator style."""
    iterator = getattr(resp, iterator_attr) if iterator_attr else resp
    events: list[Any] = []

    if hasattr(iterator, "__aiter__"):
        async for event in iterator:  # type: ignore[has-type]
            events.append(event)
    elif isinstance(iterator, Iterable):
        for event in iterator:
            events.append(event)
    else:
        raise TypeError(f"Cannot iterate response events for {type(resp)}")

    return events


@pytest.mark.anyio
@pytest.mark.parametrize("framework_name,module_path,iterator_attr", FRAMEWORKS)
@pytest.mark.parametrize(
    "variant",
    ["sync_value", "sync_generator", "async_value", "async_generator"],
)
async def test_datastar_response_matrix(
    framework_name: str, module_path: str, iterator_attr: str | None, variant: str
) -> None:
    """Ensure decorator works for sync/async and generator/non-generator functions."""
    if framework_name in {"quart", "sanic"}:
        pytest.skip(f"{framework_name} decorator requires full request context to exercise")
    if framework_name == "django":
        from django.conf import settings

        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8")

    mod = _require_module(module_path)
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

    result = handler()
    try:
        if inspect.isawaitable(result):
            result = await result

        assert isinstance(result, DatastarResponse)
        events = await _collect_events(result, iterator_attr)
        assert events, "Expected at least one event from response iterator"
    finally:
        # Avoid "coroutine was never awaited" warnings when assertions fail
        if inspect.iscoroutine(result):
            result.close()
