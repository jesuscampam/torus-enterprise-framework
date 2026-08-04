"""Pruebas unitarias de backend/sdk/scaffolder.py (ModuleScaffolder)."""

from __future__ import annotations

import ast
from pathlib import Path

from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.scaffolder import ModuleScaffold, ModuleScaffolder, write_to_disk


def test_scaffold_generates_init_module_and_readme() -> None:
    scaffold = ModuleScaffolder().scaffold(module_id="demo", name="Demo")

    assert set(scaffold.files) == {
        "demo/__init__.py",
        "demo/module.py",
        "demo/README.md",
    }


def test_scaffold_module_file_is_valid_python() -> None:
    scaffold = ModuleScaffolder().scaffold(
        module_id="demo", name="Demo", category=ModuleCategory.DATABASE
    )

    ast.parse(scaffold.files["demo/module.py"])  # no debe lanzar SyntaxError


def test_scaffold_module_file_references_module_base() -> None:
    scaffold = ModuleScaffolder().scaffold(module_id="demo", name="Demo")

    assert "ModuleBase" in scaffold.files["demo/module.py"]
    assert "class DemoModule(ModuleBase):" in scaffold.files["demo/module.py"]


def test_scaffold_readme_references_template_name() -> None:
    scaffold = ModuleScaffolder().scaffold(
        module_id="demo", name="Demo", category=ModuleCategory.AI
    )

    assert "AI Module" in scaffold.files["demo/README.md"]


def test_scaffold_module_id_with_underscores_produces_valid_class_name() -> None:
    scaffold = ModuleScaffolder().scaffold(module_id="demo_module", name="Demo Module")

    module_source = scaffold.files["demo_module/module.py"]
    ast.parse(module_source)
    assert "class DemoModuleModule(ModuleBase):" in module_source


def test_write_to_disk_materializes_all_files(tmp_path: Path) -> None:
    scaffold = ModuleScaffolder().scaffold(module_id="demo", name="Demo")

    written = write_to_disk(scaffold, tmp_path)

    assert len(written) == 3
    assert (tmp_path / "demo" / "module.py").read_text(encoding="utf-8") == scaffold.files[
        "demo/module.py"
    ]
    assert (tmp_path / "demo" / "README.md").exists()
    assert (tmp_path / "demo" / "__init__.py").exists()


def test_write_to_disk_returns_written_paths(tmp_path: Path) -> None:
    scaffold = ModuleScaffold(module_id="demo", files={"demo/x.txt": "hello"})

    written = write_to_disk(scaffold, tmp_path)

    assert written == (tmp_path / "demo" / "x.txt",)
