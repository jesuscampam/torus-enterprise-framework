"""Auditoría de vulnerabilidades de las dependencias (Sprint 2.9.2).

    python scripts/check_dependency_audit.py
    python scripts/check_dependency_audit.py --list-accepted

Ejecuta ``pip-audit`` sobre ``requirements.txt`` y falla si aparece alguna
vulnerabilidad conocida que **no** esté explícitamente aceptada en
``docs/security/accepted-vulnerabilities.json``.

Hasta Sprint 2.9.2 este control no existía, y su ausencia no era neutra: la
revisión de seguridad de Sprint 2.9.1 concluyó «versiones recientes, ningún
aviso conocido» a partir de conocimiento, no de una verificación. Al
ejecutar la herramienta por primera vez aparecieron avisos reales en dos
paquetes. Esa es exactamente la diferencia entre creer y comprobar.

Sobre las excepciones, que es donde este tipo de puerta suele degradarse:
aceptar una vulnerabilidad **no** consiste en silenciarla. Cada entrada del
fichero de aceptadas exige identificador, paquete, versión afectada, versión
que la corrige, severidad, justificación y fecha de revisión; la puerta lista
todas las aceptadas en cada ejecución, de modo que nunca desaparecen de la
vista. Una vulnerabilidad nueva —no listada— hace fallar la puerta.

Se invoca como ``python -m pip_audit`` a propósito, igual que ``mypy``: el
ejecutable suelto del PATH puede pertenecer a otro intérprete y auditar un
conjunto de paquetes distinto del que realmente se ejecuta.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = REPOSITORY_ROOT / "requirements.txt"
ACCEPTED_PATH = REPOSITORY_ROOT / "docs" / "security" / "accepted-vulnerabilities.json"

#: Segundos antes de abandonar. ``pip-audit`` consulta la base de datos de
#: avisos por red; en un entorno sin salida se cuelga en vez de fallar.
TIMEOUT_SECONDS = 600


@dataclass(frozen=True, slots=True)
class Finding:
    """Una vulnerabilidad encontrada en un paquete instalado."""

    package: str
    version: str
    identifier: str
    fix_versions: tuple[str, ...]

    @property
    def key(self) -> str:
        return f"{self.package}:{self.identifier}"

    def describe(self) -> str:
        arreglo = ", ".join(self.fix_versions) if self.fix_versions else "sin corrección publicada"
        return f"{self.package} {self.version} — {self.identifier} (corrige: {arreglo})"


def load_accepted() -> dict[str, dict[str, str]]:
    """Vulnerabilidades aceptadas, indexadas por ``paquete:identificador``."""
    if not ACCEPTED_PATH.exists():
        return {}
    data = json.loads(ACCEPTED_PATH.read_text(encoding="utf-8"))
    #: La fecha de revisión vive una sola vez en la cabecera del fichero: se
    #: revisan todas juntas al abrir un Sprint, no una a una.
    revisado = str(data.get("reviewed", "?"))
    return {
        f"{e['package']}:{e['id']}": {"reviewed": revisado, **e}
        for e in data.get("accepted", [])
        if "package" in e and "id" in e
    }


def run_pip_audit() -> tuple[list[Finding], str]:
    """Ejecuta ``pip-audit``. Devuelve ``(hallazgos, error)``; ``error`` vacío si fue bien."""
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--requirement",
                str(REQUIREMENTS),
                "--progress-spinner",
                "off",
                "--format",
                "json",
            ],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return [], "pip-audit no está instalado (pip install -r requirements-dev.txt)."
    except subprocess.TimeoutExpired:
        return [], f"pip-audit no respondió en {TIMEOUT_SECONDS}s (¿sin acceso a la red?)."

    if not completed.stdout.strip():
        return [], f"pip-audit no devolvió resultados. {completed.stderr.strip()[:400]}"

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return [], f"Salida de pip-audit ilegible: {completed.stdout[:400]}"

    hallazgos: dict[str, Finding] = {}
    for dependency in payload.get("dependencies", []):
        for vulnerability in dependency.get("vulns", []):
            finding = Finding(
                package=dependency["name"],
                version=dependency.get("version", "?"),
                identifier=vulnerability["id"],
                fix_versions=tuple(vulnerability.get("fix_versions") or ()),
            )
            # pip-audit puede repetir el mismo aviso desde varias fuentes.
            hallazgos.setdefault(finding.key, finding)
    return sorted(hallazgos.values(), key=lambda f: (f.package, f.identifier)), ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoría de dependencias de TEAF.")
    parser.add_argument(
        "--list-accepted", action="store_true", help="Lista las excepciones y termina."
    )
    args = parser.parse_args(argv)

    accepted = load_accepted()

    if args.list_accepted:
        if not accepted:
            print("No hay vulnerabilidades aceptadas.")
            return 0
        for key, entry in sorted(accepted.items()):
            print(f"  {key}  [{entry.get('severity', '?')}]  → {entry.get('target_version', '?')}")
            print(f"      {entry.get('justification', '(sin justificación)')}")
        return 0

    findings, error = run_pip_audit()
    if error:
        print(f"❌ No se pudo auditar: {error}")
        return 1

    nuevas = [f for f in findings if f.key not in accepted]
    conocidas = [f for f in findings if f.key in accepted]

    if conocidas:
        print(f"ℹ️  {len(conocidas)} vulnerabilidad(es) aceptada(s) y documentada(s):")
        for finding in conocidas:
            entry = accepted[finding.key]
            print(f"   {finding.describe()}")
            print(
                f"      severidad: {entry.get('severity', '?')} · "
                f"objetivo: {entry.get('target_version', '?')} · "
                f"revisado: {entry.get('reviewed', '?')}"
            )

    if nuevas:
        print(f"\n❌ {len(nuevas)} vulnerabilidad(es) NO aceptada(s):")
        for finding in nuevas:
            print(f"   {finding.describe()}")
        print(
            f"\nActualice la dependencia, o —si no es posible ahora— documente la excepción "
            f"con su justificación en {ACCEPTED_PATH.relative_to(REPOSITORY_ROOT)}."
        )
        return 1

    print(f"\nOK — sin vulnerabilidades nuevas ({len(conocidas)} aceptada(s) bajo seguimiento).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
