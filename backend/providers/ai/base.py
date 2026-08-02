"""``BaseAIProvider`` — clase base para implementaciones de ``AIProvider``.

Ver docs/diagrams/ai-provider-architecture.mmd. Sin lógica adicional sobre
el contrato: expone únicamente su identidad (``provider_name``), a la
espera de una implementación concreta (OpenAI, Azure OpenAI, Anthropic,
Gemini, Ollama) en un Sprint posterior.
"""

from __future__ import annotations

from abc import ABC

from backend.contracts.ai import AIProvider


class BaseAIProvider(AIProvider, ABC):
    """Base común para proveedores de IA concretos."""

    #: Nombre identificador del proveedor concreto (p. ej. "openai", "ollama").
    provider_name: str = "unset"
