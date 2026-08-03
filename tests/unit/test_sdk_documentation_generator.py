"""Pruebas unitarias de backend/sdk/documentation_generator.py (ModuleDocumentationGenerator)."""

from __future__ import annotations

from backend.sdk.builder import ModuleBuilder
from backend.sdk.documentation_generator import ModuleDocumentationGenerator


class _Greeter:
    pass


def test_generate_includes_header_fields() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo", display_name="Demo Module")
        .with_version("1.0.0")
        .with_description("Módulo de ejemplo.")
        .with_author("TEAF Team")
        .with_license("MIT")
        .build()
    )

    doc = ModuleDocumentationGenerator().generate(manifest)

    assert "# Demo Module" in doc
    assert "Módulo de ejemplo." in doc
    assert "`demo`" in doc
    assert "`1.0.0`" in doc
    assert "TEAF Team" in doc


def test_generate_omits_empty_sections() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").build()

    doc = ModuleDocumentationGenerator().generate(manifest)

    assert "## Capacidades" not in doc
    assert "## Servicios" not in doc
    assert "## Dependencias" not in doc
    assert "## Configuración" not in doc
    assert "## Health Checks" not in doc
    assert "## Eventos" not in doc
    assert "## Compatibilidad" in doc


def test_generate_includes_populated_sections() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .add_capability(id="demo.cap", name="demo-cap", description="Hace algo")
        .add_service(_Greeter, lambda c: _Greeter(), description="Sirve algo")
        .add_dependency(module_id="core", version_constraint="1.0.0")
        .add_configuration(key="LEVEL", required=True, description="Nivel")
        .add_healthcheck(name="demo.ping", description="Ping")
        .add_event("demo.happened")
        .build()
    )

    doc = ModuleDocumentationGenerator().generate(manifest)

    assert "## Capacidades" in doc
    assert "`demo.cap`" in doc
    assert "## Servicios" in doc
    assert "`_Greeter`" in doc
    assert "## Dependencias" in doc
    assert "`core`" in doc
    assert "## Configuración" in doc
    assert "`LEVEL`" in doc
    assert "## Health Checks" in doc
    assert "`demo.ping`" in doc
    assert "## Eventos" in doc
    assert "`demo.happened`" in doc


def test_generate_includes_tags_and_documentation_link() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .with_tags("db", "sql")
        .with_documentation("docs/demo/DEMO.md")
        .build()
    )

    doc = ModuleDocumentationGenerator().generate(manifest)

    assert "**Tags**: db, sql" in doc
    assert "**Documentación**: docs/demo/DEMO.md" in doc


def test_generate_marks_experimental_and_deprecated() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").as_experimental().as_deprecated().build()

    doc = ModuleDocumentationGenerator().generate(manifest)

    assert "Experimental" in doc
    assert "Deprecado" in doc
