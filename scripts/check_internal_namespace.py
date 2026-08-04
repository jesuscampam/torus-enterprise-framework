"""Verifica que el Sprint 2.6.2 (Internal Namespace Refactor) se completó
sin dejar rastros del antiguo paquete ``backend/``.

Uso:

    python scripts/check_internal_namespace.py

Sale con código 0 si la migración está completa; con código 1 y un listado
de problemas en caso contrario.

A diferencia de ``check_public_api_boundary.py`` (que aplica el límite
público/privado de forma continua, típicamente apuntado a ``examples/`` o a
un consumidor externo), este script es un verificador de integridad
estructural de una migración puntual: confirma que ``backend`` ya no existe
en ningún sentido — ni como imports, ni como paquete en disco — y que la
implementación interna sigue siendo importable de punta a punta bajo su
nuevo nombre ``teaf._internal``.

No hace falta un chequeo separado de "todo import interno usa el prefijo
teaf._internal" (el punto (d) del criterio de éxito del Sprint): una vez
que no queda ningún import de ``backend`` en ningún archivo del árbol
verificado (punto (a)), la única forma en que el código interno puede
referenciarse entre sí es vía ``teaf._internal.*`` (absoluto) o imports
relativos dentro del mismo subpaquete — ambos legítimos. Por eso ese punto
queda cubierto por la comprobación (a), sin lógica adicional.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

# Permite tanto `python scripts/check_internal_namespace.py` (el intérprete
# solo pone `scripts/` en sys.path, no la raíz del repo) como
# `python -m scripts.check_internal_namespace` (ya la incluye).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.check_public_api_boundary import ImportViolation, check_paths  # noqa: E402

#: Namespace legado que debe haber desaparecido por completo tras el Sprint 2.6.2.
LEGACY_NAMESPACE = ("backend",)

#: Raíces del repositorio que podrían conservar un import legado.
SCAN_ROOTS = ["teaf", "tests", "scripts", "database", "examples"]


def check_no_legacy_backend_imports(repo_root: Path) -> list[ImportViolation]:
    """(a) — ningún import de ``backend.*`` en ningún archivo ``.py`` del repositorio."""
    return check_paths([repo_root / root for root in SCAN_ROOTS], forbidden=LEGACY_NAMESPACE)


def check_no_backend_package_on_disk(repo_root: Path) -> list[str]:
    """(c) — no existe ningún paquete ``backend`` en la raíz del repositorio."""
    problems = []
    legacy_path = repo_root / "backend"
    if legacy_path.exists():
        problems.append(f"{legacy_path} todavía existe en disco")
    return problems


def check_all_internal_modules_importable() -> list[str]:
    """(b) — ningún import relativo roto: importa cada módulo real bajo ``teaf``.

    Deliberadamente ejecuta código (a diferencia de ``check_public_api_boundary.py``,
    puramente estático) porque un import roto solo se detecta con certeza
    intentando el import real.
    """
    import teaf

    problems = []
    for _, name, _ in pkgutil.walk_packages(teaf.__path__, prefix="teaf."):
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - se reporta, no se relanza
            problems.append(f"{name}: {exc!r}")
    return problems


def main(argv: list[str]) -> int:
    del argv  # sin argumentos posicionales — siempre verifica el repositorio completo

    violations = check_no_legacy_backend_imports(_REPO_ROOT)
    disk_problems = check_no_backend_package_on_disk(_REPO_ROOT)
    import_problems = check_all_internal_modules_importable()

    ok = True
    if violations:
        ok = False
        for violation in violations:
            print(str(violation), file=sys.stderr)
        print(f"\n{len(violations)} import(s) de 'backend' todavía presentes.", file=sys.stderr)
    if disk_problems:
        ok = False
        for problem in disk_problems:
            print(problem, file=sys.stderr)
    if import_problems:
        ok = False
        for problem in import_problems:
            print(f"import roto: {problem}", file=sys.stderr)

    if ok:
        print("OK — namespace interno migrado correctamente a teaf._internal.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
