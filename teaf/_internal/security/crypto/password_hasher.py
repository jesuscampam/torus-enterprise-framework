"""Implementaciones de ``PasswordHasher`` (ver contracts/security.py).

``Argon2PasswordHasher`` es el proveedor por defecto (recomendación OWASP
vigente, ganador de la Password Hashing Competition); ``BcryptPasswordHasher``
queda disponible para compatibilidad con hashes preexistentes de una
aplicación migrada a TEAF — el contrato ``PasswordHasher`` no distingue
cuál está activo, ver ADR-007.
"""

from __future__ import annotations

import argon2
import bcrypt as bcrypt_lib
from argon2 import exceptions as argon2_exceptions

from teaf._internal.contracts.security import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    """Argon2id vía ``argon2-cffi`` — proveedor por defecto de la plataforma."""

    def __init__(
        self, *, time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 4
    ) -> None:
        """``time_cost``/``memory_cost``/``parallelism`` son los parámetros de coste de
        Argon2id — los valores por defecto son los recomendados por OWASP para 2024+;
        ajustables por entorno vía ``SecuritySettings`` (más coste en producción, menos
        en tests para no ralentizar la suite)."""
        self._hasher = argon2.PasswordHasher(
            time_cost=time_cost, memory_cost=memory_cost, parallelism=parallelism
        )

    def hash(self, password: str) -> str:
        """Devuelve el hash PHC-encoded de ``password`` (incluye algoritmo y parámetros)."""
        return str(self._hasher.hash(password))

    def verify(self, password: str, hashed: str) -> bool:
        """``True`` si ``password`` corresponde a ``hashed`` — nunca lanza en caso de fallo."""
        try:
            self._hasher.verify(hashed, password)
        except (argon2_exceptions.VerifyMismatchError, argon2_exceptions.InvalidHashError):
            return False
        return True

    def needs_rehash(self, hashed: str) -> bool:
        """``True`` si ``hashed`` se generó con parámetros de coste más débiles que los actuales."""
        return bool(self._hasher.check_needs_rehash(hashed))


class BcryptPasswordHasher(PasswordHasher):
    """BCrypt vía ``bcrypt`` — proveedor alternativo (compatibilidad con hashes preexistentes)."""

    def __init__(self, *, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash(self, password: str) -> str:
        """Devuelve el hash BCrypt (``$2b$...``) de ``password``."""
        salt = bcrypt_lib.gensalt(rounds=self._rounds)
        return str(bcrypt_lib.hashpw(password.encode("utf-8"), salt).decode("utf-8"))

    def verify(self, password: str, hashed: str) -> bool:
        """``True`` si ``password`` corresponde a ``hashed`` — nunca lanza en caso de fallo."""
        try:
            return bool(bcrypt_lib.checkpw(password.encode("utf-8"), hashed.encode("utf-8")))
        except ValueError:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """``True`` si el coste codificado en ``hashed`` es menor que ``rounds`` actual."""
        try:
            current_rounds = int(hashed.split("$")[2])
        except (IndexError, ValueError):
            return True
        return current_rounds < self._rounds
