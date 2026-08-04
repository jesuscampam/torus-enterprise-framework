"""Capability Model — Sprint 2.4 (Platform Intelligence).

Modelo de datos y registro para que el framework pueda **describirse a sí
mismo**: qué capacidades existen, a qué categoría pertenecen, quién las
provee y en qué estado están. Ninguna capacidad real se registra en este
Sprint — solo la infraestructura para hacerlo.

Como el resto de ``backend/runtime/``, este subpaquete no importa
``backend/contracts/`` ni ``backend/providers/`` (ver
docs/runtime/RUNTIME.md) — ``CapabilityProviderRegistry`` usa un
``typing.Protocol`` estructural local en vez de importar el contrato
``CapabilityProvider`` de ``backend/contracts/``.
"""
