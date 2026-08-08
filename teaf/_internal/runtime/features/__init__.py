"""Feature Flags — Sprint 2.4 (Platform Intelligence).

Modelo de datos y gestor para que el framework pueda activar/desactivar
funcionalidades en tiempo de ejecución sin desplegar código nuevo. Sin
persistencia en este Sprint: todo vive en memoria y se reinicia con el
proceso — un Sprint futuro puede añadir un ``FeatureFlagProvider`` que lea
de base de datos o de un servicio externo sin cambiar este contrato.

Como el resto de ``backend/runtime/``, este subpaquete no importa
``backend/contracts/`` ni ``backend/providers/``.
"""
