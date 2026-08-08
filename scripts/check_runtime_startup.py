"""Comprobación de arranque real de la aplicación (Sprint 2.9.1).

La única puerta de calidad que **ejecuta** el framework de extremo a
extremo en lugar de analizarlo: construye una ``Application``, arranca su
ciclo de vida ASGI completo, llama a los cinco endpoints de sistema y la
apaga. Existe porque ninguna de las otras puertas detecta un fallo de
cableado — un ``lifespan`` que lanza, un router que no se registra, un
módulo que no arranca — y ese es precisamente el fallo que se descubre en
producción.

Deliberadamente **no** duplica lo que ya cubre la suite de pruebas: no
comprueba el contenido de las respuestas (eso lo hacen
``tests/integration/``), solo que el proceso arranca, responde y se apaga
sin errores. Es un *smoke test*, y su valor está en ser rápido y en no tener
excusas para no ejecutarlo.

    python scripts/check_runtime_startup.py
"""

from __future__ import annotations

import sys

#: Endpoints de sistema que toda aplicación TEAF sirve sin configuración
#: adicional, con el código que deben devolver recién arrancada.
_SYSTEM_ENDPOINTS: tuple[tuple[str, int], ...] = (
    ("/", 200),
    ("/health", 200),
    ("/live", 200),
    ("/ready", 200),
    ("/info", 200),
    ("/runtime/info", 200),
    ("/runtime/modules", 200),
)


def main() -> int:
    from fastapi.testclient import TestClient
    from teaf import Application
    from teaf._internal.config.settings import TestingSettings

    failures: list[str] = []

    try:
        application = Application(settings=TestingSettings())
    except Exception as exc:  # noqa: BLE001 — cualquier fallo aquí es el fallo a reportar
        print(f"❌ La aplicación no se pudo construir: {exc.__class__.__name__}: {exc}")
        return 1

    try:
        with TestClient(application.asgi) as client:
            for path, expected in _SYSTEM_ENDPOINTS:
                response = client.get(path)
                if response.status_code != expected:
                    failures.append(f"{path}: HTTP {response.status_code} (se esperaba {expected})")
            state = application.runtime.state.value
            if state != "running":
                failures.append(f"Runtime en estado '{state}' (se esperaba 'running')")
    except Exception as exc:  # noqa: BLE001
        print(f"❌ El ciclo de vida falló: {exc.__class__.__name__}: {exc}")
        return 1

    if application.runtime.state.value != "stopped":
        failures.append(
            f"Runtime en estado '{application.runtime.state.value}' tras apagar "
            "(se esperaba 'stopped')"
        )

    if failures:
        print("❌ El arranque no es correcto:")
        for failure in failures:
            print(f"   {failure}")
        return 1

    print(
        f"OK — la aplicación arranca, sirve los {len(_SYSTEM_ENDPOINTS)} endpoints de "
        f"sistema y se apaga limpiamente (versión {application.version})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
