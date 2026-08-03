"""Verifica que un árbol de archivos solo importa la API pública de TEAF.

Uso:

    python scripts/check_public_api_boundary.py examples/

Sale con código 0 y sin salida si no hay violaciones; con código 1 y un
listado de archivo:línea:import si encuentra alguna.

Namespaces del framework (ver docs/public-api/IMPORT-GUIDE.md):

- **Público**: ``teaf`` — la única superficie que cualquier consumidor
  externo de TEAF (aplicaciones construidas sobre el framework, este mismo
  repositorio en ``examples/``) debe importar.
- **Privado**: ``backend`` (y todo lo que cuelga de él — ``backend.core``,
  ``backend.runtime``, ``backend.sdk``, ``backend.contracts``,
  ``backend.providers``, ``backend.modules``, ...) — implementación interna
  del framework, sin ninguna garantía de estabilidad entre versiones fuera
  de lo que ``teaf/`` reexporta explícitamente.

Es deliberadamente estático y basado en ``ast`` (nunca ejecuta el código
inspeccionado) — sienta la base para una futura verificación automática en
CI (ver Sprint 2.5.1, sección 8, "preparar la base para futuras
verificaciones automáticas"); no está cableado a ningún pipeline todavía.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

#: Namespace público — la única raíz de import permitida para el código
#: verificado por esta utilidad.
PUBLIC_NAMESPACE = "teaf"

#: Namespaces privados — implementación interna, nunca importada directamente
#: fuera de ``teaf/`` ni de las pruebas de caja blanca del propio framework.
PRIVATE_NAMESPACES = ("backend",)


@dataclass(frozen=True, slots=True)
class ImportViolation:
    """Un import prohibido encontrado en un archivo."""

    path: Path
    line: int
    module: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: import prohibido de namespace privado '{self.module}'"


def iter_python_files(root: Path) -> Iterator[Path]:
    """Todos los archivos ``.py`` bajo ``root`` (recursivo), en orden estable."""
    if root.is_file():
        if root.suffix == ".py":
            yield root
        return
    yield from sorted(root.rglob("*.py"))


def _imported_root_modules(node: ast.Import | ast.ImportFrom) -> Iterator[str]:
    """Los nombres de paquete raíz importados por un nodo ``Import``/``ImportFrom``."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name.split(".")[0]
    else:
        # ``from . import x`` / ``from .foo import x`` (imports relativos, level > 0)
        # nunca apuntan a un namespace externo — no pueden violar el límite.
        if node.level == 0 and node.module:
            yield node.module.split(".")[0]


def find_forbidden_imports(
    source: str, *, path: Path, forbidden: Iterable[str] = PRIVATE_NAMESPACES
) -> list[ImportViolation]:
    """Analiza ``source`` (contenido de ``path``) y devuelve cada import prohibido.

    Estático: usa ``ast.parse``, nunca importa ni ejecuta ``source``.
    """
    forbidden_set = set(forbidden)
    tree = ast.parse(source, filename=str(path))
    violations: list[ImportViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        for root_module in _imported_root_modules(node):
            if root_module in forbidden_set:
                violations.append(ImportViolation(path=path, line=node.lineno, module=root_module))
    return violations


def check_paths(paths: Iterable[Path]) -> list[ImportViolation]:
    """Verifica todos los archivos ``.py`` bajo cada ruta de ``paths``."""
    violations: list[ImportViolation] = []
    for root in paths:
        for file_path in iter_python_files(root):
            source = file_path.read_text(encoding="utf-8")
            violations.extend(find_forbidden_imports(source, path=file_path))
    return violations


def main(argv: list[str]) -> int:
    if not argv:
        print(f"Uso: python {Path(__file__).name} <ruta> [<ruta> ...]", file=sys.stderr)
        return 2

    violations = check_paths(Path(arg) for arg in argv)
    if not violations:
        print(f"OK — ningún import de namespace privado {PRIVATE_NAMESPACES} encontrado.")
        return 0

    for violation in violations:
        print(str(violation), file=sys.stderr)
    print(
        f"\n{len(violations)} violación(es) — usa '{PUBLIC_NAMESPACE}' en su lugar "
        "(ver docs/public-api/IMPORT-GUIDE.md).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
