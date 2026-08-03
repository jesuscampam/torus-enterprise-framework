"""Punto de entrada ejecutable del framework.

Esta es también la "Reference Application" del Sprint 2.1 (ver
docs/architecture/FRAMEWORK-BLUEPRINT.md): mientras TEAF no tenga módulos de
negocio que integrar, la propia aplicación de bootstrap —creada por la
Application Factory de ``backend/core/application.py``— sirve como
aplicación mínima de referencia para validar que el framework arranca
correctamente. No contiene lógica de negocio.

Ejecutar desde la raíz del repositorio:

    uvicorn backend.main:app --reload

(El comando se ejecuta como ``backend.main:app``, no ``app.main:app``, para
respetar la estructura de carpetas ya aprobada en Sprint 1 — ver el reporte
de cierre de Sprint 2.1 para el detalle de esta decisión.)
"""

from __future__ import annotations

from backend.core.application import create_app

app = create_app()
