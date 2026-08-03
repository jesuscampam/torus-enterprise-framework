"""Contrato de conocimiento del framework — preparación para IA (Sprint 2.4, ítem 14).

Forma que tendrá, en un Sprint futuro, un componente capaz de responder
preguntas sobre TEAF apoyándose en su propia introspección (Runtime API,
``RuntimeSelfDescription``, manifest) — sin implementar IA en este Sprint,
solo el contrato que esa futura implementación deberá cumplir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping


class FrameworkKnowledgeProvider(ABC):
    """Expone el conocimiento del framework en forma consultable."""

    @abstractmethod
    async def describe_framework(self) -> Mapping[str, object]:
        """Devuelve una fotografía estructurada del framework (módulos, capacidades, estado)."""
        ...

    @abstractmethod
    async def answer_question(self, question: str) -> str:
        """Responde ``question`` en lenguaje natural, usando el conocimiento del framework."""
        ...
