"""``ObservabilityConfiguration`` — configuración del ``ObservabilityModule``.

Mismo criterio que ``modules/security/configuration.py``: se resuelve
desde un ``Mapping`` (``from_mapping``, típicamente
``ModuleContext.configuration``) y no importa ``config/`` directamente,
para mantener la independencia del resto de ``sdk/`` — una aplicación
concreta decide si construye esta configuración a partir de
``Settings`` (``settings.model_dump()``) o de otra fuente.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


def _coerce_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_float(value: object, default: float) -> float:
    return default if value is None else float(str(value))


def _coerce_int(value: object, default: int) -> int:
    return default if value is None else int(str(value))


def _coerce_str(value: object, default: str) -> str:
    return default if value is None else str(value)


def _coerce_optional_str(value: object) -> str | None:
    return None if value is None else str(value)


@dataclass(frozen=True, slots=True)
class ObservabilityConfiguration:
    """Configuración de recurso (Resource), muestreo y exportadores."""

    service_name: str = "teaf"
    service_version: str = "0.0.0"
    environment: str = "development"

    tracing_enabled: bool = True
    metrics_enabled: bool = True

    #: Fracción de trazas raíz muestreadas (``ParentBased(TraceIdRatioBased)``)
    #: — 1.0 (por defecto) muestrea el 100%, sensato para arrancar sin
    #: configuración adicional; producción con alto volumen normalmente baja
    #: este valor.
    sampling_ratio: float = 1.0

    #: Habilitado por defecto — igual criterio que ``DatabaseModule()``/
    #: ``SecurityModule()``: la plataforma debe funcionar "de fábrica" sin
    #: exigir un backend externo ya desplegado (ver ADR-008).
    console_exporter_enabled: bool = True

    otlp_exporter_enabled: bool = False
    otlp_traces_endpoint: str | None = None
    otlp_metrics_endpoint: str | None = None
    otlp_headers: Mapping[str, str] = field(default_factory=dict)
    otlp_timeout_seconds: float | None = None

    prometheus_exporter_enabled: bool = False
    prometheus_prefix: str = ""

    #: Intervalo de exportación periódica de métricas (Console/OTLP), en ms.
    metrics_export_interval_millis: int = 60_000

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> ObservabilityConfiguration:
        """Construye la configuración desde un ``Mapping`` (claves ausentes usan el default)."""
        otlp_headers_value = values.get("otlp_headers")
        otlp_timeout_value = values.get("otlp_timeout_seconds")
        return cls(
            service_name=_coerce_str(values.get("service_name"), "teaf"),
            service_version=_coerce_str(values.get("service_version"), "0.0.0"),
            environment=_coerce_str(values.get("environment"), "development"),
            tracing_enabled=_coerce_bool(values.get("tracing_enabled"), True),
            metrics_enabled=_coerce_bool(values.get("metrics_enabled"), True),
            sampling_ratio=_coerce_float(values.get("sampling_ratio"), 1.0),
            console_exporter_enabled=_coerce_bool(values.get("console_exporter_enabled"), True),
            otlp_exporter_enabled=_coerce_bool(values.get("otlp_exporter_enabled"), False),
            otlp_traces_endpoint=_coerce_optional_str(values.get("otlp_traces_endpoint")),
            otlp_metrics_endpoint=_coerce_optional_str(values.get("otlp_metrics_endpoint")),
            otlp_headers=otlp_headers_value if isinstance(otlp_headers_value, Mapping) else {},
            otlp_timeout_seconds=(
                float(str(otlp_timeout_value)) if otlp_timeout_value is not None else None
            ),
            prometheus_exporter_enabled=_coerce_bool(
                values.get("prometheus_exporter_enabled"), False
            ),
            prometheus_prefix=_coerce_str(values.get("prometheus_prefix"), ""),
            metrics_export_interval_millis=_coerce_int(
                values.get("metrics_export_interval_millis"), 60_000
            ),
        )
