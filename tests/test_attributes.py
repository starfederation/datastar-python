from __future__ import annotations

import json
import math
import unittest

from datastar_py.attributes import JSExpression, javascript
from datastar_py.attributes import attribute_generator as ds


class AttributeJavascriptTests(unittest.TestCase):
    def test_expression_apis_parenthesize_ambiguous_values(self) -> None:
        cases = (
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
                ds.signals(
                    items1=["first", "second"],
                    items2=["first, second"],
                    items3="first, second",
                ),
                {
                    "data-signals": (
                        '{"items1": ["first", "second"], "items2": ["first, second"], "items3": "first, second"}'
                    )
                },
            ),
            (
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
                ds.signals(
                    {
                        "items1": ["first", "second"],
                        "items2": ["first, second"],
                        "items3": "first, second",
                        "expressions_": False,
                    },
                    expressions_=True,
                ),
                {
                    "data-signals": (
                        '{"items1": [(first), (second)], "items2": [(first, second)], "items3": (first, second), "expressions_": false}'
                    )
                },
            ),
            (
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
        )

        for attribute, expected in cases:
            with self.subTest(attribute=next(iter(attribute))):
                self.assertEqual(dict(attribute), expected)

    def test_expression_apis_wrap_values_explicitly(self) -> None:
        cases = (
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
        )

        for attribute, expected in cases:
            with self.subTest(attribute=next(iter(attribute))):
                self.assertEqual(dict(attribute), expected)

    def test_expression_signals_recurse_through_nested_lists(self) -> None:
        self.assertEqual(
            dict(
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
            ),
            {
                "data-signals": (
                    '{"form": {"total": (2 * 3), "items": [($first), ($second)], '
                    '"groups": [[($third)]]}}'
                )
            },
        )

    def test_literal_signals_remain_data_and_escape_action_tokens(self) -> None:
        signals = {
            "signal_example": "$otherSignal",
            "action_example": '@post("/sse")',
            "email_example": "person@example.com",
            "expression_example": "1 + 1",
            "quoted_example": 'a "quoted" value',
        }

        rendered = dict(ds.signals(signals))["data-signals"]
        assert isinstance(rendered, str)

        self.assertEqual(
            rendered,
            "".join(
                [
                    '{"signal_example": "$otherSignal", ',
                    '"action_example": "\\u0040post(\\"/sse\\")", ',
                    '"email_example": "person@example.com", ',
                    '"expression_example": "1 + 1", ',
                    '"quoted_example": "a \\"quoted\\" value"}',
                ]
            ),
        )
        self.assertEqual(json.loads(rendered), signals)

    def test_mapping_values_serialize_recursively(self) -> None:
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

        self.assertEqual(
            javascript(value),
            '{"literal": "text", "nested": {"items": [true, false, null, 3], "expression": (1 + 1)}}',
        )

    def test_mapping_keys_are_strings_and_escaped_as_data(self) -> None:
        with self.assertRaisesRegex(TypeError, "object keys must be strings"):
            javascript({1: "value"})

        self.assertEqual(
            javascript(
                {
                    'quote"\\snow雪': "value",
                    '@post("key")': "action-looking key",
                }
            ),
            '{"quote\\"\\\\snow\\u96ea": "value", "\\u0040post(\\"key\\")": "action-looking key"}',
        )

    def test_non_finite_signal_values_are_rejected_in_both_modes(self) -> None:
        for expressions in (False, True):
            for value in (math.nan, math.inf, -math.inf):
                with (
                    self.subTest(expressions=expressions, value=value),
                    self.assertRaises(ValueError),
                ):
                    ds.signals({"value": value}, expressions_=expressions)
