"""``api/`` — la plataforma de protección y gobernanza de APIs de TEAF (Sprint 2.9, ADR-009).

Rate limiting, quotas, CORS, versionado, validación de peticiones,
compresión, idempotencia y auditoría: ocho subsistemas independientes
entre sí que ``ApiGateway`` (``api/gateway/``) compone en una única
cadena de protección, y que ``ApiProtectionModule`` (``api/module/``)
empaqueta como módulo del Runtime. Expuesto públicamente vía ``teaf.api``
(``teaf/api.py``) — nada de este paquete se importa directamente."""

from __future__ import annotations
