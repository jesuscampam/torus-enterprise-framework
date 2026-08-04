"""``runtime.manifest.json`` — manifiesto generado del Runtime (Sprint 2.4, ítem 9).

Fotografía completa y serializable de la instancia en ejecución: todo lo
que ``Framework``, ``Version``, ``Modules``, ``Capabilities``, ``Services``,
``Plugins``, ``Configuration`` y ``Feature Flags`` describen ya en la
Runtime API (``backend/runtime/api.py``), más tres hechos **estáticos** de
arquitectura — ``Contracts``, ``Providers``, ``Factories`` — que no viven en
el Runtime en sí (son nombres de clases de ``backend/contracts/`` y
``backend/providers/``).

Esos tres campos se listan como constantes de texto, deliberadamente **sin
importar** ``backend/contracts/`` ni ``backend/providers/`` — mantener esa
frontera es lo que permite que ``Runtime`` siga sin depender de ellos (ver
docs/runtime/RUNTIME.md). Quien añada un contrato/proveedor/factory nuevo
actualiza estas constantes a mano, igual que ya se actualiza
``docs/architecture/MODULE-CATALOG.md`` al añadir un módulo.
"""

from __future__ import annotations

import json
from pathlib import Path

from teaf._internal.runtime.api import (
    build_capabilities_payload,
    build_features_payload,
    build_modules_payload,
    build_plugins_payload,
    build_services_payload,
)
from teaf._internal.runtime.runtime import Runtime

#: Interfaces (``ABC``) declaradas en ``backend/contracts/`` a fecha de este Sprint.
KNOWN_CONTRACTS: tuple[str, ...] = (
    "AIProvider",
    "CapabilityProvider",
    "DatabaseProvider",
    "FrameworkKnowledgeProvider",
    "NotificationProvider",
    "Repository",
    "SchedulerProvider",
    "AuthenticationProvider",
    "AuthorizationProvider",
    "StorageProvider",
    "TelemetryProvider",
    "UnitOfWork",
)

#: Subpaquetes de ``backend/providers/`` a fecha de este Sprint.
KNOWN_PROVIDERS: tuple[str, ...] = ("ai", "database", "security", "storage", "telemetry")

#: Clases ``Factory`` declaradas en ``backend/providers/`` a fecha de este Sprint.
KNOWN_FACTORIES: tuple[str, ...] = ("DatabaseFactory", "SecurityFactory")


def generate_manifest(
    runtime: Runtime, *, configuration_summary: dict[str, object] | None = None
) -> dict[str, object]:
    """Construye el manifiesto del Runtime en el momento de la llamada.

    Toda la información dinámica (módulos, capacidades, servicios, plugins,
    feature flags) se lee del ``Runtime`` — nada queda hardcodeado salvo los
    tres hechos estáticos de arquitectura documentados arriba.
    """
    return {
        "framework": "TEAF",
        "version": runtime.framework_version,
        "runtime": runtime.self_description().as_dict(),
        "modules": build_modules_payload(runtime),
        "capabilities": build_capabilities_payload(runtime),
        "services": build_services_payload(runtime),
        "plugins": build_plugins_payload(runtime),
        "configuration": configuration_summary or {},
        "featureFlags": build_features_payload(runtime),
        "contracts": list(KNOWN_CONTRACTS),
        "providers": list(KNOWN_PROVIDERS),
        "factories": list(KNOWN_FACTORIES),
    }


def write_manifest(
    runtime: Runtime,
    path: Path,
    *,
    configuration_summary: dict[str, object] | None = None,
) -> Path:
    """Genera el manifiesto y lo escribe como JSON en ``path``. Devuelve ``path``."""
    manifest = generate_manifest(runtime, configuration_summary=configuration_summary)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
