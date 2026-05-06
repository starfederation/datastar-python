from collections.abc import Mapping
from typing import Annotated, Any, Literal, overload

from fastapi import Depends
from fastapi.sse import ServerSentEvent

from datastar_py import consts
from datastar_py.attributes import SignalValue

from .sse import SSE_HEADERS, BaseServerSentEventGenerator, _HtmlProvider
from .starlette import read_signals

__all__ = [
    "SSE_HEADERS",
    "ReadSignals",
    "ServerSentEventGenerator",
    "read_signals",
]


ReadSignals = Annotated[dict[str, Any] | None, Depends(read_signals)]


class ServerSentEventGenerator(BaseServerSentEventGenerator):
    __slots__ = ()

    @overload
    @classmethod
    def patch_elements(
        cls,
        *,
        selector: str,
        mode: Literal[consts.ElementPatchMode.REMOVE],
        use_view_transition: bool | None = None,
        event_id: str | None = None,
        retry_duration: int | None = None,
    ) -> ServerSentEvent: ...
    @overload
    @classmethod
    def patch_elements(
        cls,
        elements: str | _HtmlProvider,
        selector: str | None = None,
        mode: consts.ElementPatchMode | None = None,
        use_view_transition: bool | None = None,
        event_id: str | None = None,
        retry_duration: int | None = None,
    ) -> ServerSentEvent: ...
    @classmethod
    def patch_elements(  # noqa: PLR0913 too many arguments
        cls,
        elements: str | _HtmlProvider | None = None,
        selector: str | None = None,
        mode: consts.ElementPatchMode | None = None,
        use_view_transition: bool | None = None,
        namespace: consts.ElementPatchNamespace | None = None,
        event_id: str | None = None,
        retry_duration: int | None = None,
    ) -> ServerSentEvent:
        result = cls._patch_elements(
            elements=elements,
            selector=selector,
            mode=mode,
            use_view_transition=use_view_transition,
            event_id=event_id,
            namespace=namespace,
            retry_duration=retry_duration,
        )
        return ServerSentEvent(
            event=result["event_type"],
            id=result["event_id"],
            raw_data="\n".join(result["data_lines"]),
            retry=result["retry_duration"],
        )

    @classmethod
    def remove_elements(
        cls, selector: str, event_id: str | None = None, retry_duration: int | None = None
    ) -> ServerSentEvent:
        result = cls._remove_elements(
            selector=selector,
            event_id=event_id,
            retry_duration=retry_duration,
        )
        return ServerSentEvent(
            event=result["event_type"],
            id=result["event_id"],
            raw_data="\n".join(result["data_lines"]),
            retry=result["retry_duration"],
        )

    @classmethod
    def patch_signals(
        cls,
        signals: dict[str, SignalValue] | str,
        event_id: str | None = None,
        only_if_missing: bool | None = None,
        retry_duration: int | None = None,
    ) -> ServerSentEvent:
        result = cls._patch_signals(
            signals=signals,
            event_id=event_id,
            only_if_missing=only_if_missing,
            retry_duration=retry_duration,
        )
        return ServerSentEvent(
            event=result["event_type"],
            id=result["event_id"],
            raw_data="\n".join(result["data_lines"]),
            retry=result["retry_duration"],
        )

    @classmethod
    def execute_script(
        cls,
        script: str,
        auto_remove: bool = True,
        attributes: Mapping[str, str] | list[str] | None = None,
        event_id: str | None = None,
        retry_duration: int | None = None,
    ) -> ServerSentEvent:
        result = cls._execute_script(
            script=script,
            auto_remove=auto_remove,
            attributes=attributes,
            event_id=event_id,
            retry_duration=retry_duration,
        )
        return ServerSentEvent(
            event=result["event_type"],
            id=result["event_id"],
            raw_data="\n".join(result["data_lines"]),
            retry=result["retry_duration"],
        )

    @classmethod
    def redirect(cls, location: str) -> ServerSentEvent:
        result = cls._redirect(location)
        return ServerSentEvent(
            event=result["event_type"],
            id=result["event_id"],
            raw_data="\n".join(result["data_lines"]),
            retry=result["retry_duration"],
        )
