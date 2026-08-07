"""Proveedores de compresión de respuestas (Sprint 2.9, ADR-009).

GZip se implementa sobre ``gzip`` de la librería estándar: siempre
disponible, sin dependencias nuevas. Brotli se implementa igual de completo,
pero sobre un paquete **opcional** (``brotli`` o ``brotlicffi``), porque
Python no lo trae de serie y añadir una dependencia dura al framework exige
su propio ADR (CLAUDE.md, sección 4). El resultado práctico es el mismo para
quien lo necesita —``pip install brotli`` y ``BrotliCompressionProvider``
funciona— sin imponer el coste a quien no.

``CompressionNegotiator`` es quien decide qué proveedor usar en cada
respuesta: lee ``Accept-Encoding``, descarta los no disponibles y respeta el
umbral mínimo de tamaño. Comprimir una respuesta de 200 bytes cuesta más CPU
de lo que ahorra en red, de ahí que el umbral por defecto no sea 0.
"""

from __future__ import annotations

import gzip
import importlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from teaf._internal.api.models import CompressionAlgorithm
from teaf._internal.contracts.api import CompressionProvider


def _load_brotli() -> Any | None:
    """Módulo Brotli disponible, o ``None`` si no hay ninguno instalado.

    ``brotli`` (implementación C de Google) y ``brotlicffi`` (binding CFFI,
    el que usa PyPy) exponen la misma función ``compress`` — sirve
    cualquiera de las dos. Se resuelve en una función, y no con un
    ``try/except import`` a nivel de módulo, para poder sustituirlo en
    pruebas sin manipular ``sys.modules``.
    """
    for module_name in ("brotli", "brotlicffi"):
        try:
            return importlib.import_module(module_name)
        except ImportError:
            continue
    return None


#: Resuelto una sola vez al importar: buscar el módulo en cada compresión
#: costaría una consulta a ``sys.modules`` por respuesta servida.
_brotli: Any | None = _load_brotli()


class GzipCompressionProvider(CompressionProvider):
    """Compresión GZip sobre la librería estándar — siempre disponible.

    ``level`` va de 1 (más rápido) a 9 (más pequeño); 6 es el equilibrio por
    defecto de ``gzip`` y el que usan la mayoría de servidores web.
    """

    def __init__(self, *, level: int = 6) -> None:
        self._level = level

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.GZIP

    @property
    def available(self) -> bool:
        return True

    @property
    def level(self) -> int:
        """Nivel de compresión configurado."""
        return self._level

    def compress(self, data: bytes) -> bytes:
        # mtime=0 hace la salida determinista: sin ello, dos ejecuciones del
        # mismo contenido producen bytes distintos y ni las cachés ni las
        # pruebas pueden compararlas.
        return gzip.compress(data, compresslevel=self._level, mtime=0)


class BrotliCompressionProvider(CompressionProvider):
    """Compresión Brotli sobre el paquete opcional ``brotli``/``brotlicffi``.

    Comprime entre un 15% y un 25% mejor que GZip en contenido de texto, que
    es la razón por la que todo navegador moderno lo anuncia. Si el paquete
    no está instalado, ``available`` es ``False`` y el negociador
    simplemente no lo elige — la respuesta sale sin comprimir o en GZip, en
    vez de fallar.
    """

    def __init__(self, *, quality: int = 4) -> None:
        """``quality`` va de 0 a 11. El 4 es el habitual para compresión al
        vuelo: Brotli con calidad 11 es mucho más lento que GZip y solo tiene
        sentido para contenido estático precomprimido."""
        self._quality = quality

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.BROTLI

    @property
    def available(self) -> bool:
        return _brotli is not None

    @property
    def quality(self) -> int:
        """Calidad de compresión configurada."""
        return self._quality

    def compress(self, data: bytes) -> bytes:
        """Comprime ``data``.

        Raises:
            RuntimeError: si Brotli no está instalado en este intérprete.
        """
        if _brotli is None:
            raise RuntimeError(
                "Brotli no está disponible: instala 'brotli' (o 'brotlicffi') para usar "
                "BrotliCompressionProvider, o usa GzipCompressionProvider."
            )
        compressed: bytes = _brotli.compress(data, quality=self._quality)
        return compressed


def parse_accept_encoding(value: str) -> tuple[str, ...]:
    """Codificaciones aceptadas por el cliente, ordenadas por preferencia (``q``).

    ``"br;q=1.0, gzip;q=0.8"`` → ``("br", "gzip")``. Una codificación con
    ``q=0`` está explícitamente rechazada y se descarta.
    """
    candidates: list[tuple[float, int, str]] = []
    for position, part in enumerate(value.split(",")):
        token, _, params = part.strip().partition(";")
        token = token.strip().lower()
        if not token:
            continue
        quality = 1.0
        if params.strip().startswith("q="):
            try:
                quality = float(params.strip()[2:])
            except ValueError:
                quality = 1.0
        if quality <= 0.0:
            continue
        # ``position`` desempata manteniendo el orden declarado por el cliente
        # entre codificaciones de igual calidad.
        candidates.append((-quality, position, token))
    return tuple(token for _, _, token in sorted(candidates))


@dataclass(frozen=True, slots=True)
class CompressionPolicy:
    """Cuándo y con qué comprimir.

    ``compressible_types`` limita la compresión a contenido que realmente se
    beneficia: comprimir un JPEG o un ZIP gasta CPU para no ahorrar nada, y
    en el peor caso agranda la respuesta.
    """

    enabled: bool = True
    #: Por debajo de este tamaño no se comprime — el ahorro no compensa la CPU
    #: ni las ~20 bytes de cabecera del propio formato comprimido.
    minimum_size_bytes: int = 500
    compressible_types: tuple[str, ...] = (
        "text/",
        "application/json",
        "application/xml",
        "application/javascript",
        "image/svg+xml",
    )

    def is_compressible(self, content_type: str | None) -> bool:
        """``True`` si un contenido de tipo ``content_type`` merece comprimirse."""
        if not content_type:
            return False
        lowered = content_type.split(";", 1)[0].strip().lower()
        return any(lowered.startswith(prefix) for prefix in self.compressible_types)


class CompressionNegotiator:
    """Elige el proveedor de compresión de cada respuesta.

    Recibe los proveedores en orden de preferencia del *servidor*; la
    preferencia del *cliente* (``Accept-Encoding``) manda sobre ella, que es
    lo que exige HTTP.
    """

    def __init__(
        self,
        providers: Sequence[CompressionProvider] = (),
        *,
        policy: CompressionPolicy | None = None,
    ) -> None:
        self._providers = tuple(p for p in providers if p.available)
        self._policy = policy or CompressionPolicy()

    @property
    def providers(self) -> tuple[CompressionProvider, ...]:
        """Proveedores realmente disponibles en este intérprete."""
        return self._providers

    @property
    def policy(self) -> CompressionPolicy:
        """Política aplicada por este negociador."""
        return self._policy

    def select(
        self, *, accept_encoding: str, content_type: str | None, content_length: int
    ) -> CompressionProvider | None:
        """Proveedor a usar, o ``None`` si la respuesta no debe comprimirse."""
        if not self._policy.enabled or not self._providers:
            return None
        if content_length < self._policy.minimum_size_bytes:
            return None
        if not self._policy.is_compressible(content_type):
            return None

        accepted = parse_accept_encoding(accept_encoding)
        by_token = {p.algorithm.value: p for p in self._providers}
        for token in accepted:
            if token == "*":
                return self._providers[0]
            provider = by_token.get(token)
            if provider is not None:
                return provider
        return None
