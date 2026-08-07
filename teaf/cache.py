"""``teaf.cache`` — almacén clave-valor con expiración, en memoria o sobre Redis.

Fachada sobre ``teaf/_internal/modules/cache/`` y ``teaf/_internal/providers/cache/``
(Sprint 3.0, ADR-012). Una aplicación que solo corre en una instancia no
necesita nada de aquí: el backend por defecto es en memoria y TEAF arranca
sin infraestructura desplegada.

Se exporta porque hay una necesidad concreta y actual, no por simetría: en
cuanto una aplicación se despliega con más de una réplica, los almacenes en
memoria de la plataforma de protección de APIs pasan a ser por proceso, y un
límite de 100 peticiones por minuto con 4 réplicas son 400 en la práctica.
Para arreglarlo hay que poder construir un proveedor de caché y dárselo a
``ApiProtectionModule(cache_provider=...)`` — y eso, sin estos símbolos, solo
se puede hacer importando ``teaf._internal.*``, que es exactamente lo que la
fachada existe para evitar.

``CacheModule`` **sí** se exporta, a diferencia de ``DatabaseModule``/
``SecurityModule``/``ObservabilityModule`` y por el mismo motivo que
``ApiProtectionModule`` (ver ``teaf/api.py``): todo el valor de la caché
distribuida está en que alguien abra la conexión al arrancar y la cierre al
apagar. Obligar a recomponer ese ciclo de vida a mano en cada aplicación no
desacopla nada; solo reparte por ahí conexiones que nadie cierra.

Nomenclatura, igual que en ``teaf.api``:

- ``CacheProvider`` es el **contrato**; ``InMemoryCacheProvider`` y
  ``RedisCacheProvider`` son las implementaciones. Quien resuelve
  ``CacheProvider`` del contenedor no sabe —ni necesita saber— cuál hay
  detrás.
- ``RedisCacheProvider`` requiere el extra opcional ``teaf[redis]``. El
  import de ``redis`` es perezoso: construir el proveedor sin el paquete
  instalado no falla; falla al conectar, con un mensaje que dice qué
  instalar.
- La URL de Redis suele llevar credenciales, así que se configura por
  variable de entorno (``CACHE_REDIS_URL``) o gestor de secretos, nunca en
  el repositorio — ver SECURITY-STANDARD.md §9 y
  docs/modules/cache/CACHE.md.
"""

from __future__ import annotations

from teaf._internal.contracts.cache import CacheProvider
from teaf._internal.modules.cache.configuration import CacheBackend, CacheConfiguration
from teaf._internal.modules.cache.module import CacheModule
from teaf._internal.providers.cache.memory import InMemoryCacheProvider
from teaf._internal.providers.cache.redis import RedisCacheConfiguration, RedisCacheProvider

__all__ = [
    "CacheBackend",
    "CacheConfiguration",
    "CacheModule",
    "CacheProvider",
    "InMemoryCacheProvider",
    "RedisCacheConfiguration",
    "RedisCacheProvider",
]
