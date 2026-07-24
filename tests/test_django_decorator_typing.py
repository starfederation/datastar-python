"""Static typing regression tests for Django datastar_response overloads."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent / "typing_fixtures" / "django_decorator.py"


@pytest.mark.skipif(importlib.util.find_spec("mypy") is None, reason="mypy not installed")
@pytest.mark.skipif(importlib.util.find_spec("django") is None, reason="django not installed")
def test_django_datastar_response_mypy_overloads() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--hide-error-context",
            "--no-error-summary",
            str(FIXTURE_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert (
        'Revealed type is "def (request: django.http.request.HttpRequest) '
        '-> datastar_py.django.DatastarResponse"'
    ) in output
    assert output.count(
        'Revealed type is "def (request: django.http.request.HttpRequest) '
        '-> typing.Coroutine[Any, Any, datastar_py.django.DatastarResponse]"'
    ) == 2
