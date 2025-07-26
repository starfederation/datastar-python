from __future__ import annotations

from typing import Literal, TypedDict, Unpack

from datastar_py.attributes import JSExpression, JSRegex, SignalValue, _js_object


class _FetchOptions(TypedDict, total=False):
    content_type: Literal["json", "form"]
    include_signals: str
    exclude_signals: str
    selector: str
    headers: dict[str, str]
    open_when_hidden: bool
    retry_interval: int
    retry_scalar: float
    retry_max_wait_ms: int
    retry_max_count: int
    request_cancellation: Literal["auto", "disabled"] | str


def _fetch(
    method: Literal["get", "post", "put", "patch", "delete"],
    url: str,
    **options: Unpack[_FetchOptions],
) -> str:
    result = f"@{method}('{url}'"
    if options:
        mapped_options = {}
        if "content_type" in options:
            mapped_options["contentType"] = options["content_type"]
        if "include_signals" in options or "exclude_signals" in options:
            filter_signals = {}
            if "include_signals" in options:
                filter_signals["include"] = JSRegex(options["include_signals"])
            if "exclude_signals" in options:
                filter_signals["exclude"] = JSRegex(options["exclude_signals"])
            mapped_options["filterSignals"] = filter_signals
        if "selector" in options:
            mapped_options["selector"] = options["selector"]
        if "headers" in options:
            mapped_options["headers"] = _js_object(options["headers"])
        if "open_when_hidden" in options:
            mapped_options["openWhenHidden"] = options["open_when_hidden"]
        if "retry_interval" in options:
            mapped_options["retryInterval"] = options["retry_interval"]
        if "retry_scalar" in options:
            mapped_options["retryScalar"] = options["retry_scalar"]
        if "retry_max_wait_ms" in options:
            mapped_options["retryMaxWaitMs"] = options["retry_max_wait_ms"]
        if "request_cancellation" in options:
            if options["request_cancellation"] in ("auto", "disabled"):
                mapped_options["requestCancellation"] = options["request_cancellation"]
            else:
                mapped_options["requestCancellation"] = JSExpression(
                    options["request_cancellation"]
                )
        result += f", {_js_object(mapped_options)}"
    result += ")"
    return result


def get(url: str, **options: Unpack[_FetchOptions]) -> str:
    return _fetch("get", url, **options)


def post(url: str, **options: Unpack[_FetchOptions]) -> str:
    return _fetch("post", url, **options)


def put(url: str, **options: Unpack[_FetchOptions]) -> str:
    return _fetch("put", url, **options)


def patch(url: str, **options: Unpack[_FetchOptions]) -> str:
    return _fetch("patch", url, **options)


def delete(url: str, **options: Unpack[_FetchOptions]) -> str:
    return _fetch("delete", url, **options)


def peek(expression: str) -> str:
    """Evaluate an expression containing signals without subscribing to changes in those signals."""
    return f"@peek(() => {expression})"


def set_all(value: SignalValue, include: str | None = None, exclude: str | None = None) -> str:
    """Set the value of all matching signals."""
    filter_dict = {}
    if include:
        filter_dict["include"] = JSRegex(include)
    if exclude:
        filter_dict["exclude"] = JSRegex(exclude)
    filter_string = f", {_js_object(filter_dict)}" if filter_dict else ""
    return f"@setAll({value}{filter_string})"


def toggle_all(include: str | None = None, exclude: str | None = None) -> str:
    """Toggle the boolean value of all matching signals."""
    filter_dict = {}
    if include:
        filter_dict["include"] = JSRegex(include)
    if exclude:
        filter_dict["exclude"] = JSRegex(exclude)
    filter_string = _js_object(filter_dict) if filter_dict else ""
    return f"@toggleAll({filter_string})"


def clipboard(text: str, is_base_64: bool = False) -> str:
    """PRO: Copy text to the clipboard."""
    return f"@clipboard({text}{', true' if is_base_64 else ''})"


def fit(
    value: float | str,
    old_min: float | str,
    old_max: float | str,
    new_min: float | str,
    new_max: float | str,
    should_clamp: bool = False,
    should_round: bool = False,
) -> str:
    """PRO: Linearly interpolate a value from one range to another."""
    return f"@fit({value}, {old_min}, {old_max}, {new_min}, {new_max}, {'true' if should_clamp else 'false'}{', true' if should_round else ''})"
