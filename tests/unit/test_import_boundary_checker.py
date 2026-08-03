"""Pruebas unitarias de scripts/check_public_api_boundary.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.check_public_api_boundary import (  # noqa: E402
    ImportViolation,
    check_paths,
    find_forbidden_imports,
    iter_python_files,
    main,
)


def test_find_forbidden_imports_flags_plain_import() -> None:
    violations = find_forbidden_imports("import backend.core.application\n", path=Path("x.py"))
    assert len(violations) == 1
    assert violations[0].module == "backend"
    assert violations[0].line == 1


def test_find_forbidden_imports_flags_from_import() -> None:
    violations = find_forbidden_imports(
        "from backend.sdk.module_base import ModuleBase\n", path=Path("x.py")
    )
    assert len(violations) == 1
    assert violations[0].module == "backend"


def test_find_forbidden_imports_allows_teaf_import() -> None:
    violations = find_forbidden_imports("from teaf import Application\n", path=Path("x.py"))
    assert violations == []


def test_find_forbidden_imports_allows_stdlib_and_third_party() -> None:
    source = "import asyncio\nfrom typing import cast\nfrom fastapi import FastAPI\n"
    assert find_forbidden_imports(source, path=Path("x.py")) == []


def test_find_forbidden_imports_ignores_relative_imports() -> None:
    """Un import relativo (``from . import x``) nunca puede apuntar a un namespace externo."""
    violations = find_forbidden_imports("from . import sibling\n", path=Path("pkg/x.py"))
    assert violations == []


def test_find_forbidden_imports_reports_correct_line_number() -> None:
    source = "import asyncio\n\nimport backend.core\n"
    violations = find_forbidden_imports(source, path=Path("x.py"))
    assert violations[0].line == 3


def test_find_forbidden_imports_respects_custom_forbidden_set() -> None:
    violations = find_forbidden_imports("import teaf\n", path=Path("x.py"), forbidden=("teaf",))
    assert len(violations) == 1
    assert violations[0].module == "teaf"


def test_import_violation_str_is_human_readable() -> None:
    violation = ImportViolation(path=Path("a/b.py"), line=5, module="backend")
    text = str(violation)
    assert "a/b.py" in text
    assert "5" in text
    assert "backend" in text


def test_iter_python_files_on_single_file(tmp_path: Path) -> None:
    file_path = tmp_path / "a.py"
    file_path.write_text("import teaf\n")
    assert list(iter_python_files(file_path)) == [file_path]


def test_iter_python_files_ignores_non_python_single_file(tmp_path: Path) -> None:
    file_path = tmp_path / "a.txt"
    file_path.write_text("not python")
    assert list(iter_python_files(file_path)) == []


def test_iter_python_files_recurses_into_directories(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    top = tmp_path / "top.py"
    nested = tmp_path / "pkg" / "nested.py"
    top.write_text("import teaf\n")
    nested.write_text("import teaf\n")
    found = set(iter_python_files(tmp_path))
    assert found == {top, nested}


def test_check_paths_reports_violations_across_multiple_files(tmp_path: Path) -> None:
    good = tmp_path / "good.py"
    bad = tmp_path / "bad.py"
    good.write_text("from teaf import Application\n")
    bad.write_text("from backend.core.application import create_app\n")

    violations = check_paths([tmp_path])
    assert len(violations) == 1
    assert violations[0].path == bad


def test_check_paths_empty_when_clean(tmp_path: Path) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text("from teaf import Application\n")
    assert check_paths([tmp_path]) == []


def test_main_returns_zero_and_prints_ok_on_clean_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "clean.py").write_text("from teaf import Application\n")
    exit_code = main([str(tmp_path)])
    assert exit_code == 0
    assert "OK" in capsys.readouterr().out


def test_main_returns_one_and_prints_violations_on_dirty_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "dirty.py").write_text("from backend.sdk.module_base import ModuleBase\n")
    exit_code = main([str(tmp_path)])
    assert exit_code == 1
    assert "backend" in capsys.readouterr().err


def test_main_returns_two_without_arguments() -> None:
    assert main([]) == 2


def test_examples_directory_has_no_forbidden_imports() -> None:
    """El límite público/privado, aplicado a los ejemplos reales del repositorio."""
    repository_root = Path(__file__).resolve().parents[2]
    violations = check_paths([repository_root / "examples"])
    assert violations == []
