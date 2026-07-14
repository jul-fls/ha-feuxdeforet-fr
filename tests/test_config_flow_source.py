"""Regression tests for the Home Assistant options flow."""

from __future__ import annotations

import ast
from pathlib import Path

CONFIG_FLOW_PATH = Path("custom_components/feuxdeforet_fr/config_flow.py")


def test_options_flow_does_not_assign_config_entry() -> None:
    """Home Assistant owns the read-only OptionsFlow.config_entry property."""
    tree = ast.parse(CONFIG_FLOW_PATH.read_text(encoding="utf-8"))

    assignments = [
        node for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.AnnAssign))
    ]

    assert not any(
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "self"
        and target.attr == "config_entry"
        for assignment in assignments
        for target in (
            assignment.targets
            if isinstance(assignment, ast.Assign)
            else [assignment.target]
        )
    )


def test_options_flow_is_created_without_config_entry_argument() -> None:
    """The framework injects the config entry after constructing the flow."""
    tree = ast.parse(CONFIG_FLOW_PATH.read_text(encoding="utf-8"))

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FeuxDeForetOptionsFlow"
    ]

    assert len(calls) == 1
    assert not calls[0].args
    assert not calls[0].keywords
