"""Verifica que un árbol de archivos solo importa la API pública de TEAF.

Uso:

    python scripts/check_public_api_boundary.py examples/

Sale con código 0 y sin salida si no hay violaciones; con código 1 y un
listado de archivo:línea:import si encuentra alguna.

Namespaces del framework (ver docs/public-api/IMPORT-GUIDE.md):

- **Público**: ``teaf`` — la única superficie que cualquier consumidor
  externo de TEAF (aplicaciones construidas sobre el framework, este mismo
  repositorio en ``examples/``) debe importar.
- **Privado**: ``teaf._internal`` (y todo lo que cuelga de él —
  ``teaf._internal.core``, ``teaf._internal.runtime``, ``teaf._internal.sdk``,
  ``teaf._internal.contracts``, ``teaf._internal.providers``,
  ``teaf._internal.modules``, ...) — implementación interna del framework,
  movida desde el antiguo paquete de nivel superior ``backend/`` en el
  Sprint 2.6.2 (ver ADR-006), sin ninguna garantía de estabilidad entre
  versiones fuera de lo que ``teaf/`` reexporta explícitamente.

Como ``teaf._internal`` es un namespace de dos segmentos (no una raíz de
paquete distinta como el antiguo ``backend``), la coincidencia se hace por
**prefijo punteado**, no solo por la raíz del import — así se distingue
``from teaf._internal.core import x`` (prohibido) de ``from teaf import
Application`` (permitido), algo imposible con una comparación de solo la
raíz.

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
PRIVATE_NAMESPACES = ("teaf._internal",)


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


def _imported_candidate_paths(node: ast.Import | ast.ImportFrom) -> Iterator[str]:
    """Rutas punteadas candidatas a verificar contra el namespace prohibido.

    Para ``ast.Import`` es la ruta completa de cada alias (p. ej.
    ``teaf._internal.core.application``). Para ``ast.ImportFrom`` con import
    absoluto (``level == 0``) incluye tanto el módulo base solo — para
    detectar ``from teaf._internal import x`` — como cada combinación
    módulo+alias — para detectar ``from teaf._internal.core import x`` y
    también la evasión por atributo ``from teaf import _internal``.
    """
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name
    else:
        # ``from . import x`` / ``from .foo import x`` (imports relativos, level > 0)
        # nunca apuntan a un namespace externo — no pueden violar el límite.
        if node.level == 0 and node.module:
            yield node.module
            for alias in node.names:
                yield f"{node.module}.{alias.name}"


def _matched_forbidden(path: str, forbidden: Iterable[str]) -> str | None:
    """El namespace prohibido de ``forbidden`` que ``path`` viola, si alguno.

    Coincidencia por prefijo punteado: ``path`` viola ``entry`` si es
    exactamente ``entry`` o cuelga de él (``entry.algo``, ``entry.algo.mas``).
    """
    for entry in forbidden:
        if path == entry or path.startswith(f"{entry}."):
            return entry
    return None


def find_forbidden_imports(
    source: str, *, path: Path, forbidden: Iterable[str] = PRIVATE_NAMESPACES
) -> list[ImportViolation]:
    """Analiza ``source`` (contenido de ``path``) y devuelve cada import prohibido.

    Estático: usa ``ast.parse``, nunca importa ni ejecuta ``source``. Reporta
    como máximo una violación por namespace prohibido distinto y por nodo de
    import — varias rutas candidatas del mismo nodo (p. ej. módulo base y
    módulo+alias de un mismo ``from ... import ...``) que coinciden con el
    mismo namespace prohibido no se duplican.
    """
    forbidden_tuple = tuple(forbidden)
    tree = ast.parse(source, filename=str(path))
    violations: list[ImportViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        matched_for_node: set[str] = set()
        for candidate in _imported_candidate_paths(node):
            matched = _matched_forbidden(candidate, forbidden_tuple)
            if matched is not None and matched not in matched_for_node:
                matched_for_node.add(matched)
                violations.append(ImportViolation(path=path, line=node.lineno, module=matched))
    return violations


def check_paths(
    paths: Iterable[Path], *, forbidden: Iterable[str] | None = None
) -> list[ImportViolation]:
    """Verifica todos los archivos ``.py`` bajo cada ruta de ``paths``.

    ``forbidden`` permite verificar contra un conjunto de namespaces
    prohibidos distinto de ``PRIVATE_NAMESPACES`` (p. ej.
    ``scripts/check_internal_namespace.py`` lo usa con ``("backend",)`` para
    confirmar que no sobrevive ningún import del namespace legado) sin
    duplicar el recorrido de archivos.
    """
    forbidden_tuple = tuple(forbidden) if forbidden is not None else PRIVATE_NAMESPACES
    violations: list[ImportViolation] = []
    for root in paths:
        for file_path in iter_python_files(root):
            source = file_path.read_text(encoding="utf-8")
            violations.extend(
                find_forbidden_imports(source, path=file_path, forbidden=forbidden_tuple)
            )
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
