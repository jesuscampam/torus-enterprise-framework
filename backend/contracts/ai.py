"""Contrato de proveedor de IA.

Ver docs/diagrams/ai-provider-architecture.mmd: desacopla el framework de
cualquier proveedor concreto (OpenAI, Azure OpenAI, Anthropic, Gemini,
Ollama). Sin implementación concreta en este Sprint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence


class AIProvider(ABC):
    """Generación de texto y embeddings, independiente del proveedor subyacente."""

    @abstractmethod
    async def generate_text(self, prompt: str, *, max_tokens: int | None = None) -> str:
        """Genera texto a partir de ``prompt``."""
        ...

    @abstractmethod
    async def generate_embedding(self, text: str) -> Sequence[float]:
        """Genera el vector de embedding correspondiente a ``text``."""
        ...
