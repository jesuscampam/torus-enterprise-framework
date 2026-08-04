"""Pruebas unitarias de backend/sdk/templates.py (MODULE_TEMPLATES)."""

from __future__ import annotations

from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.templates import MODULE_TEMPLATES, get_template


def test_all_seven_categories_have_a_template() -> None:
    assert set(MODULE_TEMPLATES) == set(ModuleCategory)
    assert len(MODULE_TEMPLATES) == 7


def test_get_template_returns_matching_category() -> None:
    template = get_template(ModuleCategory.DATABASE)
    assert template.category is ModuleCategory.DATABASE
    assert template.name == "Database Module"


def test_every_template_has_non_empty_name_and_description() -> None:
    for template in MODULE_TEMPLATES.values():
        assert template.name
        assert template.description


def test_template_as_dict_is_serializable() -> None:
    template = get_template(ModuleCategory.AI)
    payload = template.as_dict()
    assert payload["category"] == "ai"
    assert "suggestedCapabilities" in payload
    assert "suggestedServices" in payload
