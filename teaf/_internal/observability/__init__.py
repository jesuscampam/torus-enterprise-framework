"""``observability/`` — la plataforma de observabilidad de TEAF (Sprint 2.8, ADR-008).

Logging estructurado, tracing distribuido, métricas, health checks
agregados y diagnósticos de runtime, construidos sobre el SDK oficial de
OpenTelemetry (``opentelemetry-api``/``-sdk``) — nunca una abstracción
propia por debajo. Completa, sin reemplazar, el andamiaje de Sprint 2.1-2.4
(``core/context.py``, ``core/logging.py``, ``providers/telemetry/``,
``runtime/diagnostics.py``, ``monitoring/``). Expuesto públicamente vía
``teaf.observability`` (``teaf/observability.py``).
"""

from __future__ import annotations
