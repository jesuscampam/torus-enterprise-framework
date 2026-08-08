# ADR-006: Internal Namespace Refactor — `backend/` → `teaf/_internal/`

## Estado

Aceptado

## Contexto

TEAF se instala como un paquete Python (`pip install -e .`, Sprint 2.5.1) y expone una única API pública soportada vía `from teaf import ...`. Su implementación interna, sin embargo, seguía viviendo bajo un paquete de nivel superior separado llamado `backend/`, un nombre genérico y extremadamente común en aplicaciones Python — incluyendo, potencialmente, en las propias aplicaciones consumidoras construidas sobre TEAF (TicketGateway, Portal TORUS, Portal NOC, Portal SRE, Inventario TI, Gestor de Incidentes, integraciones SAP/Salesforce/Control-M, IA Empresarial). Cuando una aplicación consumidora define su propio paquete `backend/` en el mismo entorno de ejecución, la resolución de `import backend` pasa a depender del orden de `sys.path` — un comportamiento no determinista entre entornos de desarrollo, contenedores y despliegues, capaz de resolver silenciosamente al paquete equivocado. Este riesgo se detectó de forma concreta durante el desarrollo de una aplicación de referencia construida sobre TEAF.

## Problema

¿Cómo elimina TEAF por completo el riesgo de colisión de namespace de `backend` con el código de una aplicación consumidora, sin alterar en absoluto el contrato de la API pública `teaf.*` que esas aplicaciones ya consumen?

## Decisión

Se mueve la totalidad del paquete `backend/` (127 archivos, 12 subpaquetes reales — `config`, `contracts`, `core`, `developer`, `middleware`, `modules`, `monitoring`, `providers`, `runtime`, `sdk`, `shared`, más `main.py` — y 10 directorios reservados solo con `README.md`) a `teaf/_internal/`, como subpaquete privado de `teaf`, en vez de como paquete de nivel superior independiente:

- `backend.core.registry` pasa a `teaf._internal.core.registry`, y análogamente para el resto de subpaquetes y los directorios reservados.
- Las 9 fachadas de `teaf/` (`application.py`, `runtime.py`, `modules.py`, `services.py`, `events.py`, `configuration.py`, `capabilities.py`, `health.py`, `version.py`) actualizan sus imports de `backend.*` a `teaf._internal.*` sin ningún otro cambio — mismos símbolos, mismo `__all__`, mismo comportamiento.
- El nombre `_internal` (con guión bajo inicial) refuerza a nivel de convención Python que nada bajo esa ruta es superficie pública, complementando — no reemplazando — la aplicación real del límite: `scripts/check_public_api_boundary.py`, generalizado de coincidencia por raíz a coincidencia por prefijo punteado (necesaria porque `teaf._internal`, a diferencia del antiguo `backend`, es un namespace de dos segmentos que cuelga del propio namespace público `teaf`) y con su namespace privado por defecto repuntado de `backend` a `teaf._internal`.
- Se añade `scripts/check_internal_namespace.py`, verificador de integridad de la migración: confirma que no queda ningún import de `backend.*`, que `backend/` no existe en disco, y que todo el árbol `teaf.*` sigue siendo importable de punta a punta.
- `pyproject.toml` deja de declarar un paquete `backend*` independiente: `[tool.setuptools.packages.find].include = ["teaf*"]` descubre `teaf._internal` y todos sus subpaquetes automáticamente, por ser subpaquetes de `teaf`.
- Se descarta la alternativa de mantener `backend/` como paquete de nivel superior pero renombrarlo a algo menos genérico (por ejemplo, `_teaf_backend/`): se descarta porque no resuelve el problema de raíz — cualquier nombre de nivel superior sigue siendo, en principio, colisionable con el `sys.path` de una aplicación consumidora; anidarlo bajo `teaf.*` lo hace estructuralmente imposible de colisionar, ya que solo existe alcanzable como atributo del propio paquete `teaf`.

## Consecuencias

### Positivas

- Elimina por construcción la posibilidad de colisión de namespace entre la implementación interna de TEAF y un paquete `backend/` propio de cualquier aplicación consumidora — ya no existe un nombre `backend` de nivel superior que pueda colisionar.
- El límite público/privado (`teaf` frente a lo interno) queda reforzado en dos niveles independientes: convención de nomenclatura Python (`_internal`) y verificación estática automatizada (`scripts/check_public_api_boundary.py`, `scripts/check_internal_namespace.py`).
- Cero impacto en consumidores: la superficie pública (`teaf.__all__`) no cambia ni un carácter; ninguna aplicación construida sobre `from teaf import ...` requiere ningún cambio de código.
- Refuerza el principio ya documentado en `docs/public-api/PACKAGE-STRUCTURE.md` de que la implementación interna es libre de reorganizarse entre Sprints sin romper a ningún consumidor.
- La experiencia de desarrollador resultante es equivalente a la de frameworks maduros del ecosistema Python (Django, FastAPI, SQLAlchemy), donde la implementación privada vive anidada bajo el paquete público, nunca como paquete hermano de nivel superior.

### Negativas / Trade-offs

- Costo de migración de una sola vez: 402 líneas de import reescritas en 125 archivos, documentación y pruebas actualizadas en la misma iteración — mitigado por ser puramente mecánico (sin cambios de comportamiento) y ejecutado mediante un codemod, no a mano.
- El historial de archivos movidos requiere `git log --follow` para trazar más allá de este Sprint — trade-off estándar de cualquier reorganización de directorios, mitigado por usar `git mv` (preserva el renombrado explícitamente en el historial de Git).
- Introduce un segundo script de verificación (`check_internal_namespace.py`) además del ya existente `check_public_api_boundary.py` — se acepta la superposición parcial de propósito (ambos aplican límites de namespace) porque verifican invariantes distintos (límite de consumo permanente frente a completitud de una migración puntual) y el nuevo script reutiliza la lógica del existente en vez de duplicarla.
- Esta iteración no crea un documento `PROJECT-IDENTITY.md` separado pese a haberse considerado: su contenido ya está cubierto por `docs/public-api/IMPORT-GUIDE.md` y el docstring de `teaf/_internal/__init__.py` — crearlo habría introducido documentación duplicada.
