import json
import math

import pytest

from datastar_py.attributes import JSExpression, javascript
from datastar_py.attributes import attribute_generator as ds


@pytest.mark.parametrize(
    ("attribute", "expected"),
    (
        (
            ds.attr(title="first, second"),
            {"data-attr": '{"title": (first, second)}'},
        ),
        (
            ds.class_({"active": "first, second"}),
            {"data-class": '{"active": (first, second)}'},
        ),
        (
            ds.style(width="first, second"),
            {"data-style": '{"width": (first, second)}'},
        ),
        (
            # kwargs form with default expressions_ = False
            ds.signals(
                items1=["first", "second"],
                items2=["first, second"],
                items3="first, second",
                # expressions_ = False, # <- this is the default
            ),
            {
                "data-signals": (
                    '{"items1": ["first", "second"], "items2": ["first, second"], "items3": "first, second"}'
                )
            },
        ),
        (
            # kwargs form with expressions
            ds.signals(
                items1=["first", "second"],
                items2=["first, second"],
                items3="first, second",
                expressions_=True,
            ),
            {
                "data-signals": (
                    '{"items1": [(first), (second)], "items2": [(first, second)], "items3": (first, second)}'
                )
            },
        ),
        (
            # dict form with tuples
            ds.signals(
                {
                    "items1": ("first", "second"),
                    "items2": ("first, second",),
                    "items3": "first, second",
                },
            ),
            {
                "data-signals": (
                    '{"items1": ["first", "second"], "items2": ["first, second"], "items3": "first, second"}'
                )
            },
        ),
        (
            # dict form with lists
            ds.signals(
                {
                    "items1": ["first", "second"],
                    "items2": ["first, second"],
                    "items3": "first, second",
                },
            ),
            {
                "data-signals": (
                    '{"items1": ["first", "second"], "items2": ["first, second"], "items3": "first, second"}'
                )
            },
        ),
        (
            # dict form with tuples and as expressions
            ds.signals(
                {
                    "items1": ("first", "second"),
                    "items2": ("first, second",),
                    "items3": "first, second",
                },
                expressions_=True,
            ),
            {
                "data-signals": (
                    '{"items1": [(first), (second)], "items2": [(first, second)], "items3": (first, second)}'
                )
            },
        ),
        (
            # dict form with lists and as expressions
            ds.signals(
                {
                    "items1": ["first", "second"],
                    "items2": ["first, second"],
                    "items3": "first, second",
                },
                expressions_=True,
            ),
            {
                "data-signals": (
                    '{"items1": [(first), (second)], "items2": [(first, second)], "items3": (first, second)}'
                )
            },
        ),
        (
            # escape double quotes appropriately
            ds.signals(
                {
                    "answer1": '{"value": 42}',
                    "answer2": {"value": 42},
                },
                expressions_=True,
            ),
            {"data-signals": ('{"answer1": ({"value": 42}), "answer2": {"value": 42}}')},
        ),
        (
            ds.signals(
                {
                    "answer1": '{"value": 42}',
                    "answer2": {"value": 42},
                },
            ),
            {"data-signals": ('{"answer1": "{\\"value\\": 42}", "answer2": {"value": 42}}')},
        ),
    ),
)
def test_expression_apis_parenthesize_ambiguous_values(attribute, expected):
    assert dict(attribute) == expected


def test_signals_support_mixed_literals_and_expressions():
    assert ds.signals(
        literal="window.innerWidth",
        expression=JSExpression("window.innerWidth"),
    ) == {"data-signals": ('{"literal": "window.innerWidth", "expression": (window.innerWidth)}')}


@pytest.mark.parametrize(
    ("attribute", "expected"),
    (
        (
            ds.attr(title='"hello"', hidden="$closed"),
            {"data-attr": '{"title": ("hello"), "hidden": ($closed)}'},
        ),
        (
            ds.class_({"active item": "$selected", "plain": "true"}),
            {"data-class": '{"active item": ($selected), "plain": (true)}'},
        ),
        (
            ds.style(width="$width + 'px'"),
            {"data-style": "{\"width\": ($width + 'px')}"},
        ),
        (
            ds.signals({"form": {"count": "1 + 1"}}),
            {"data-signals": '{"form": {"count": "1 + 1"}}'},
        ),
        (
            ds.signals({"form": {"count": "1 + 1"}}, expressions_=True),
            {"data-signals": '{"form": {"count": (1 + 1)}}'},
        ),
    ),
)
def test_expression_apis_wrap_values_explicitly(attribute, expected):
    assert dict(attribute) == expected


def test_expression_signals_recurse_through_nested_lists():
    assert dict(
        ds.signals(
            {
                "form": {
                    "total": "2 * 3",
                    "items": ["$first", "$second"],
                    "groups": [["$third"]],
                }
            },
            expressions_=True,
        )
    ) == {
        "data-signals": (
            '{"form": {"total": (2 * 3), "items": [($first), ($second)], "groups": [[($third)]]}}'
        )
    }


def test_literal_signals_remain_data_and_escape_action_tokens():
    signals = {
        "signal_example": "$otherSignal",
        "action_example": '@post("/sse")',
        "email_example": "person@example.com",
        "expression_example": "1 + 1",
        "quoted_example": 'a "quoted" value',
    }

    rendered = dict(ds.signals(signals))["data-signals"]
    assert isinstance(rendered, str)

    assert rendered == "".join(
        [
            '{"signal_example": "$otherSignal", ',
            '"action_example": "@post(\\"/sse\\")", ',
            '"email_example": "person@example.com", ',
            '"expression_example": "1 + 1", ',
            '"quoted_example": "a \\"quoted\\" value"}',
        ]
    )
    assert json.loads(rendered) == signals


def test_mapping_values_serialize_recursively():
    value = {
        "literal": "text",
        "nested": {
            # These Python spellings differ from JavaScript
            # This test can catch accidental fallbacks to str()
            # instead of JSON serialization.
            "items": [True, False, None, 3],
            "expression": JSExpression("1 + 1"),
        },
    }

    assert javascript(value) == (
        '{"literal": "text", "nested": {"items": [true, false, null, 3], "expression": (1 + 1)}}'
    )


def test_mapping_keys_are_strings_and_escaped_as_data():
    with pytest.raises(TypeError, match="object keys must be strings"):
        javascript({1: "value"})

    assert (
        javascript(
            {
                'quote"\\snow雪': "value",
                '@post("key")': "action-looking key",
            }
        )
        == '{"quote\\"\\\\snow\\u96ea": "value", "@post(\\"key\\")": "action-looking key"}'
    )


@pytest.mark.parametrize("expressions", (False, True))
@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf))
def test_non_finite_signal_values_are_rejected_in_both_modes(expressions, value):
    with pytest.raises(ValueError):
        ds.signals({"value": value}, expressions_=expressions)
