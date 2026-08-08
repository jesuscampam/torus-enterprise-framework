"""Política de longitud mínima del secreto JWT (Sprint 3.0).

Sprint 2.9.2 detectó que TEAF no imponía ninguna longitud mínima al secreto
JWT: aceptaba `"test-secret"` (11 bytes) para firmar HS256 sin decir nada.
Lo destapó el ``InsecureKeyLengthWarning`` que introdujo pyjwt 2.13.0, y un
aviso que nadie lee no es una defensa.

El mínimo **no está elegido a ojo**: sale de RFC 7518 §3.2, que exige que
una clave HMAC tenga al menos el tamaño de la salida de su función hash.
Es la misma regla que aplica pyjwt en su aviso, así que la política del
framework y la de la librería no pueden divergir.

    HS256  →  SHA-256  →  32 bytes
    HS384  →  SHA-384  →  48 bytes
    HS512  →  SHA-512  →  64 bytes

Los algoritmos asimétricos (``RS*``, ``ES*``, ``PS*``, ``EdDSA``) quedan
fuera: ahí el "secreto" es una clave PEM cuya fortaleza depende del tamaño
del módulo o de la curva, no del número de bytes del texto. Medirla con la
misma regla daría un resultado sin sentido.

Este módulo no importa nada del framework a propósito. Lo consumen
``config/settings.py`` (validación de configuración, antes de arrancar) y
``security/tokens/jwt_provider.py`` (construcción directa del proveedor), y
mantenerlo sin dependencias evita que la configuración —que se importa
pronto y en todas partes— arrastre la plataforma de seguridad entera.
"""

from __future__ import annotations

#: Bytes mínimos por algoritmo HMAC, según RFC 7518 §3.2.
MINIMUM_SECRET_BYTES: dict[str, int] = {
    "HS256": 32,
    "HS384": 48,
    "HS512": 64,
}


def minimum_secret_bytes(algorithm: str) -> int:
    """Bytes mínimos exigidos a ``algorithm``. ``0`` si no es HMAC."""
    return MINIMUM_SECRET_BYTES.get(algorithm.strip().upper(), 0)


def describe_secret_violation(secret: str | None, algorithm: str) -> str | None:
    """Mensaje de error si ``secret`` incumple la política, o ``None`` si cumple.

    Devuelve texto en vez de lanzar para que cada llamante elija su propia
    excepción: la configuración lanza ``ConfigurationException`` y el
    proveedor también, pero pydantic necesita el mensaje para componer su
    propio error de validación.

    El mensaje nombra el algoritmo, la longitud recibida y la exigida —
    **nunca el secreto**, que acabaría en un log o en una traza.
    """
    required = minimum_secret_bytes(algorithm)
    if required == 0 or secret is None:
        return None

    length = len(secret.encode("utf-8"))
    if length >= required:
        return None

    return (
        f"El secreto JWT es demasiado corto para {algorithm.strip().upper()}: "
        f"{length} bytes, mínimo {required} (RFC 7518 §3.2). "
        f"Genere uno con 'python -c \"import secrets; print(secrets.token_urlsafe({required}))\"' "
        f"— ver docs/security/SECURITY-CONFIGURATION.md."
    )
