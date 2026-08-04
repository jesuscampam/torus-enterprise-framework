"""Exportadores de telemetría — implementaciones concretas de ``Exporter`` (ver ADR-008).

``console``, ``otlp`` y ``prometheus`` están completamente implementados.
``prepared`` deja preparados (contrato cumplido, sin conectividad real)
Jaeger, Zipkin, Dynatrace, Elastic, Azure Monitor, Grafana, Datadog, New
Relic y Splunk — todos alcanzables hoy mismo vía ``OtlpExporter`` + un
OpenTelemetry Collector, sin rediseño (ver ADR-008, sección Consecuencias).
"""

from __future__ import annotations
