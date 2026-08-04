"""``teaf.version`` — el único punto de verdad para toda la información de versión pública.

Cinco números de versión, independientes entre sí, cada uno respondiendo a
una pregunta de compatibilidad distinta (ver
docs/public-api/VERSIONING.md):

- ``FRAMEWORK_VERSION``: la versión de release de TEAF (``CHANGELOG.md``).
- ``SDK_VERSION``: el ``Module SDK`` (``teaf/_internal/sdk/``) que usa un autor de
  módulos — evoluciona a su propio ritmo (nuevas primitivas, nuevos
  binders) independientemente del framework.
- ``RUNTIME_VERSION``: la Runtime API (``teaf/_internal/runtime/``) que consume el SDK.
- ``MODULE_SPEC_VERSION``: ``ModuleSpecification`` (``teaf/_internal/sdk/specification.py``)
  — la forma que debe tener todo ``ModuleManifest`` para ser válido.
- ``PUBLIC_API_VERSION``: la propia superficie pública ``teaf.*`` (este
  paquete) — sube solo cuando cambia de forma incompatible alguno de los
  símbolos exportados en ``teaf/__init__.py``.

Cada constante se origina en su paquete dueño dentro de ``teaf/_internal/`` (nunca
al revés — ``teaf/_internal/`` no importa ``teaf/``, para no invertir la dirección
de dependencias e introducir un ciclo con ``teaf/application.py``, que sí
importa ``teaf._internal.core.application``); este módulo simplemente las agrega
en el único lugar donde un consumidor externo debe leerlas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from teaf._internal.core.application import FRAMEWORK_VERSION as FRAMEWORK_VERSION
from teaf._internal.runtime import RUNTIME_VERSION as RUNTIME_VERSION
from teaf._internal.sdk import SDK_VERSION as SDK_VERSION
from teaf._internal.sdk.specification import SPEC_VERSION as MODULE_SPEC_VERSION

#: Versión de la superficie pública ``teaf.*`` en sí misma (este paquete).
#: A diferencia de las otras cuatro, no tiene un "dueño" dentro de
#: ``teaf/_internal/`` — el concepto de API pública nace en este Sprint (2.5.1).
PUBLIC_API_VERSION = "1.0.0"

_VERSION_NUMBER = re.compile(r"\d+(?:\.\d+)*")
_CONSTRAINT = re.compile(r"^(==|>=|<=|~=|>|<)?(\d+(?:\.\d+)*)$")


def _numeric_parts(version: str) -> tuple[int, ...]:
    """Parte numérica inicial de ``version`` (ignora sufijos como ``-alpha``)."""
    match = _VERSION_NUMBER.match(version)
    if match is None:
        return (0,)
    return tuple(int(part) for part in match.group(0).split("."))


def is_compatible(actual_version: str, constraint: str) -> bool:
    """``True`` si ``actual_version`` cumple ``constraint``.

    ``constraint`` acepta ``"*"``/``""`` (cualquier versión), un número
    exacto (``"1.2.3"``, equivalente a ``"==1.2.3"``), o un operador
    explícito (``">=1.2"``, ``"<=2.0"``, ``"~=1.4"``, ``">1.0"``, ``"<2.0"``).
    Un ``constraint`` con una forma no reconocida se considera satisfecho
    (permisivo por diseño — igual criterio que
    ``ModuleBase._check_compatibility``, ver ``teaf/_internal/sdk/module_base.py``).

    Útil para que herramientas externas (o un futuro ``import checker`` más
    estricto) verifiquen, antes de instalar un módulo o una integración,
    si es compatible con la versión de TEAF instalada — ver
    docs/public-api/VERSIONING.md.
    """
    if constraint in ("", "*"):
        return True
    match = _CONSTRAINT.match(constraint)
    if match is None:
        return True
    operator = match.group(1) or "=="
    actual = _numeric_parts(actual_version)
    required = _numeric_parts(match.group(2))
    length = max(len(actual), len(required))
    actual = actual + (0,) * (length - len(actual))
    required = required + (0,) * (length - len(required))
    if operator == "==":
        return actual == required
    if operator == ">=":
        return actual >= required
    if operator == "<=":
        return actual <= required
    if operator == ">":
        return actual > required
    if operator == "<":
        return actual < required
    # "~=": compatible dentro de la misma versión menor.
    return actual[:-1] == required[:-1] and actual >= required


@dataclass(frozen=True, slots=True)
class Version:
    """Fotografía inmutable de los cinco números de versión públicos de TEAF.

    ``teaf.Version`` es la instancia ya construida (no la clase) — se
    consume directamente como ``teaf.Version.framework``, nunca se
    instancia de nuevo.
    """

    framework: str = FRAMEWORK_VERSION
    sdk: str = SDK_VERSION
    runtime: str = RUNTIME_VERSION
    module_spec: str = MODULE_SPEC_VERSION
    public_api: str = PUBLIC_API_VERSION

    def as_dict(self) -> dict[str, str]:
        """Representación serializable (JSON) de esta fotografía de versiones."""
        return {
            "framework": self.framework,
            "sdk": self.sdk,
            "runtime": self.runtime,
            "moduleSpec": self.module_spec,
            "publicApi": self.public_api,
        }


CURRENT_VERSION = Version()

__all__ = [
    "CURRENT_VERSION",
    "FRAMEWORK_VERSION",
    "MODULE_SPEC_VERSION",
    "PUBLIC_API_VERSION",
    "RUNTIME_VERSION",
    "SDK_VERSION",
    "Version",
    "is_compatible",
]
