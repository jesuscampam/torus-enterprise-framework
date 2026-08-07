"""Comprueba que el paquete ``teaf`` se construye (Sprint 3.0).

Es la única puerta que verifica el artefacto que de verdad se distribuye. Las
demás trabajan sobre el árbol de fuentes, donde ``import teaf`` funciona
porque el directorio actual está en ``sys.path`` — y eso oculta una clase
entera de fallos: un paquete nuevo que no entra en el wheel porque
``[tool.setuptools.packages.find]`` no lo recoge, un fichero de datos sin
declarar, o un ``pyproject.toml`` con metadatos inválidos. Nada de eso rompe
las pruebas; rompe la instalación de quien consume TEAF.

Se construye **con aislamiento**, el modo por defecto de ``build``: se crea un
entorno limpio con el backend que declara ``[build-system]``. Se probó
``--no-isolation`` para evitar la dependencia de red, y se descartó porque
reutiliza el ``setuptools`` del sistema — que en distribuciones basadas en
Debian viene parcheado y falla al construir el wheel (``AttributeError:
install_layout``). El aislamiento cuesta unos 5 segundos y hace que la puerta
mida el paquete y no las particularidades de la máquina.

Se verifica también que el wheel **contiene lo que debe**: el paquete público,
el privado y el marcador ``py.typed``. Un wheel que se construye pero llega
vacío pasaría una comprobación que solo mirase el código de salida.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

#: Rutas que tienen que viajar dentro del wheel. No es la lista completa —
#: solo lo que, si faltara, dejaría el paquete inservible sin que ninguna
#: otra puerta se enterase.
REQUIRED_MEMBERS: tuple[str, ...] = (
    "teaf/__init__.py",
    "teaf/cache.py",
    "teaf/version.py",
    "teaf/py.typed",
    "teaf/_internal/__init__.py",
)

ROOT = Path(__file__).resolve().parent.parent


def build_wheel(destination: Path) -> Path:
    """Construye el wheel en ``destination`` y devuelve su ruta."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(destination)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout[-4000:])
        print(result.stderr[-4000:], file=sys.stderr)
        raise SystemExit("❌ La construcción del paquete falló.")

    wheels = sorted(destination.glob("*.whl"))
    if not wheels:
        raise SystemExit("❌ La construcción terminó sin error pero no produjo ningún wheel.")
    return wheels[-1]


def main() -> int:
    try:
        import build  # noqa: F401, PLC0415
    except ImportError:
        print(
            "❌ Falta el paquete 'build' (dependencia de desarrollo).\n"
            "   Instálelo con: pip install build",
            file=sys.stderr,
        )
        return 1

    with tempfile.TemporaryDirectory() as workspace:
        wheel = build_wheel(Path(workspace))
        members = set(zipfile.ZipFile(wheel).namelist())
        missing = [name for name in REQUIRED_MEMBERS if name not in members]

        if missing:
            print("❌ El wheel se construyó pero le faltan ficheros imprescindibles:")
            for name in missing:
                print(f"   {name}")
            return 1

        print(f"OK — {wheel.name} construido con {len(members)} ficheros.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
