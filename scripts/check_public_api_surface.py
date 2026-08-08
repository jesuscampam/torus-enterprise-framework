"""Verificador de compatibilidad hacia atrás de la API pública (Sprint 2.9.1).

TEAF promete que ``teaf.*`` no rompe a sus consumidores entre versiones
(ver [VERSIONING.md](../docs/public-api/VERSIONING.md)). Hasta este Sprint,
esa promesa se sostenía únicamente sobre la revisión humana y sobre
``tests/unit/test_teaf_package.py``, que compara la lista de **nombres**
exportados. Un nombre que sigue existiendo pero al que se le ha quitado un
parámetro, cambiado un valor por defecto o alterado el tipo de retorno rompe
igual, y ninguna de las dos cosas lo detectaba.

Este verificador captura la **firma** de cada símbolo público —clases con
sus métodos y sus parámetros, funciones con los suyos— en un fichero de
referencia (``docs/public-api/api-surface.json``) y compara la superficie
actual contra él:

    python scripts/check_public_api_surface.py             # compara
    python scripts/check_public_api_surface.py --update    # regenera

Qué se considera una rotura, y por qué solo eso:

- **Quitar** un símbolo, un método público o un parámetro sin valor por
  defecto rompe a quien lo usaba.
- **Añadir** un parámetro *obligatorio* rompe a todo el que ya llamaba.
- **Cambiar** el valor por defecto de un parámetro cambia el comportamiento
  de quien no lo pasaba, que es una rotura silenciosa y de las peores.

Añadir un símbolo, un método o un parámetro *opcional* no rompe a nadie: se
reporta como ampliación de la superficie, no como error. Es exactamente la
asimetría que define la compatibilidad hacia atrás.
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SURFACE_PATH = REPOSITORY_ROOT / "docs" / "public-api" / "api-surface.json"


def _describe_callable(target: Any) -> dict[str, Any] | None:
    """Firma de ``target`` como datos comparables, o ``None`` si no es inspeccionable."""
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return None

    parameters = []
    for name, parameter in signature.parameters.items():
        if name in ("self", "cls"):
            continue
        parameters.append(
            {
                "name": name,
                "kind": parameter.kind.name,
                "required": parameter.default is inspect.Parameter.empty
                and parameter.kind
                not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD),
                # El valor por defecto se compara por su ``repr``: comparar los
                # objetos fallaría con cualquier default no primitivo (una
                # tupla vacía, un enum), y el ``repr`` es estable para todos
                # los que TEAF usa.
                "default": (
                    None
                    if parameter.default is inspect.Parameter.empty
                    else repr(parameter.default)
                ),
            }
        )
    return {"parameters": parameters}


def _describe_class(target: type) -> dict[str, Any]:
    """Métodos públicos de ``target`` con sus firmas."""
    methods: dict[str, Any] = {}
    for name, member in inspect.getmembers(target):
        if name.startswith("_") and name != "__init__":
            continue
        if not callable(member):
            continue
        described = _describe_callable(member)
        if described is not None:
            methods[name] = described
    return {"kind": "class", "methods": methods}


def capture_surface() -> dict[str, Any]:
    """Superficie pública actual de ``teaf``, símbolo a símbolo."""
    import teaf

    surface: dict[str, Any] = {}
    for name in sorted(teaf.__all__):
        symbol = getattr(teaf, name)
        if inspect.isclass(symbol):
            surface[name] = _describe_class(symbol)
        elif inspect.isfunction(symbol) or inspect.isbuiltin(symbol):
            described = _describe_callable(symbol)
            surface[name] = {"kind": "function", **(described or {})}
        else:
            # Constantes y singletons (``Version``, ``ANONYMOUS_PRINCIPAL``…):
            # se registra su tipo, no su valor — el valor puede cambiar entre
            # versiones (``Version`` lo hace en cada release), el tipo no.
            surface[name] = {"kind": "value", "type": type(symbol).__name__}
    return surface


def compare(previous: dict[str, Any], current: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Compara dos superficies. Devuelve ``(roturas, ampliaciones)``."""
    breaks: list[str] = []
    additions: list[str] = []

    for name in sorted(set(previous) - set(current)):
        breaks.append(f"símbolo eliminado: teaf.{name}")
    for name in sorted(set(current) - set(previous)):
        additions.append(f"símbolo nuevo: teaf.{name}")

    for name in sorted(set(previous) & set(current)):
        before, after = previous[name], current[name]
        if before.get("kind") != after.get("kind"):
            breaks.append(f"teaf.{name} cambió de {before.get('kind')} a {after.get('kind')}")
            continue
        if before.get("kind") == "class":
            breaks.extend(_compare_class(name, before, after))
            additions.extend(
                f"método nuevo: teaf.{name}.{method}"
                for method in sorted(set(after["methods"]) - set(before["methods"]))
            )
        elif before.get("kind") == "function":
            breaks.extend(_compare_parameters(f"teaf.{name}", before, after))
    return breaks, additions


def _compare_class(name: str, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    breaks: list[str] = []
    for method in sorted(set(before["methods"]) - set(after["methods"])):
        breaks.append(f"método eliminado: teaf.{name}.{method}")
    for method in sorted(set(before["methods"]) & set(after["methods"])):
        breaks.extend(
            _compare_parameters(
                f"teaf.{name}.{method}", before["methods"][method], after["methods"][method]
            )
        )
    return breaks


def _compare_parameters(label: str, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    breaks: list[str] = []
    previous = {p["name"]: p for p in before.get("parameters", [])}
    current = {p["name"]: p for p in after.get("parameters", [])}

    for parameter in sorted(set(previous) - set(current)):
        breaks.append(f"{label}: parámetro eliminado '{parameter}'")
    for parameter in sorted(set(current) - set(previous)):
        if current[parameter]["required"]:
            breaks.append(f"{label}: parámetro obligatorio nuevo '{parameter}'")
    for parameter in sorted(set(previous) & set(current)):
        was, is_now = previous[parameter], current[parameter]
        if not was["required"] and is_now["required"]:
            breaks.append(f"{label}: '{parameter}' pasó a ser obligatorio")
        if was["default"] != is_now["default"]:
            breaks.append(
                f"{label}: '{parameter}' cambió su valor por defecto "
                f"({was['default']} → {is_now['default']})"
            )
    return breaks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--update", action="store_true", help="Regenera el fichero de referencia.")
    args = parser.parse_args(argv)

    current = capture_surface()

    if args.update or not SURFACE_PATH.exists():
        SURFACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SURFACE_PATH.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
        print(f"Superficie pública guardada en {SURFACE_PATH} ({len(current)} símbolos).")
        return 0

    previous = json.loads(SURFACE_PATH.read_text())
    breaks, additions = compare(previous, current)

    if additions:
        print(f"ℹ️  {len(additions)} ampliación(es) de la superficie pública (no rompen):")
        for line in additions[:20]:
            print(f"   {line}")
        if len(additions) > 20:
            print(f"   ... y {len(additions) - 20} más")

    if breaks:
        print(f"\n❌ {len(breaks)} rotura(s) de compatibilidad hacia atrás:")
        for line in breaks:
            print(f"   {line}")
        print(
            "\nSi son intencionadas, requieren subir la versión mayor de PUBLIC_API_VERSION "
            "(ver docs/public-api/VERSIONING.md) y regenerar con --update."
        )
        return 1

    print(f"OK — la API pública ({len(current)} símbolos) es compatible hacia atrás.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
