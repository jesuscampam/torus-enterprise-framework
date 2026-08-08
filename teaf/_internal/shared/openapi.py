"""Descripciones de respuesta OpenAPI reutilizables por las rutas del framework.

Existen por una razón medida, no estética (Sprint 2.9.1). FastAPI genera un
``TypeAdapter`` de Pydantic por cada ruta a partir de su anotación de
retorno, y ese trabajo domina el arranque de la aplicación: con las 15 rutas
de sistema del framework (``/health``, ``/ready``, ``/live``, ``/``,
``/info`` y las diez de ``/runtime/*``), construir la ``Application`` cuesta
**9 veces más** con esa generación que sin ella.

Para rutas que devuelven un ``dict``/``list`` plano ese modelo no valida ni
convierte nada: el valor ya es JSON-serializable y FastAPI lo codifica igual
en ambos casos (verificado byte a byte en
``tests/unit/test_openapi_responses.py``). Así que esas rutas declaran
``response_model=None`` para saltarse la generación, y usan estas constantes
para **conservar el esquema OpenAPI** que de otro modo se perdería.

Frente a dejar que FastAPI lo genere, lo único que cambia en
``/openapi.json`` es la desaparición del campo ``title`` autogenerado
(``"Response Health Health Get"`` y similares) — un identificador derivado
del nombre de la función, no parte del contrato.
"""

from __future__ import annotations

from typing import Any

#: Respuesta ``200`` que es un objeto JSON (``dict``).
JSON_OBJECT_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/json": {"schema": {"type": "object"}}}}
}

#: Respuesta ``200`` que es un array JSON de objetos (``list[dict]``).
JSON_OBJECT_ARRAY_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {"application/json": {"schema": {"type": "array", "items": {"type": "object"}}}}
    }
}

#: Respuesta ``200`` que es un objeto JSON de valores string (``dict[str, str]``).
JSON_STRING_MAP_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {
            "application/json": {
                "schema": {"type": "object", "additionalProperties": {"type": "string"}}
            }
        }
    }
}
