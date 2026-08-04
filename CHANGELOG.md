# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

Sin cambios todavía sobre [0.7.0-alpha](#070-alpha---2026-08-04).

## [0.7.0-alpha] - 2026-08-04

### Added

- **Enterprise Security Platform** (Sprint 2.7, [ADR-007](docs/architecture/adr/ADR-007-enterprise-security-stack.md)): autenticación y autorización empresarial completas, diseñadas alrededor del contrato `IdentityProvider` — nunca acopladas a JWT ni a ningún mecanismo concreto. Ver [docs/security/SECURITY-ARCHITECTURE.md](docs/security/SECURITY-ARCHITECTURE.md).
  - **Cinco Identity Providers implementados**: Anonymous (respaldo, siempre disponible), JWT (`JWTProvider`/`JWTIdentityProvider`, access+refresh, revocación, rotación con revocación-en-reutilización, clock skew configurable), API Key (`ApiKeyProvider`/`ApiKeyIdentityProvider`, transporte por header/query string, hashing HMAC-SHA256, expiración, revocación, scopes, rotación), LDAP/Active Directory (`LDAPProvider`, bind + búsqueda de grupos + mapeo a roles/permisos, vía `ldap3` en threadpool), Azure AD/Microsoft Entra ID (`AzureADProvider`, OIDC + JWKS + Authorization Code Flow, multi-tenant con lista de tenants permitidos).
  - **`OpenIDConnectProvider`**: base OIDC genérica y reutilizable de la que `AzureADProvider` es la primera especialización — Keycloak/Auth0/Okta/Google se añadirían como subclases sin tocar `SecurityMiddleware` ni ningún otro proveedor. Contratos preparados y deliberadamente sin implementación para OAuth2 no-OIDC (`OAuth2IdentityProvider`, pensado para GitHub/Apple) y SAML (`SAMLIdentityProvider`).
  - **RBAC + políticas**: `Role`/`Permission` (reutilizados de Sprint 2.2), `StaticRoleResolver`, `RolePermissionResolver`, `PrincipalResolver`, `Policy`/`DefaultPolicyEvaluator` para reglas arbitrarias que un rol/permiso plano no puede expresar (p. ej. pertenencia a tenant).
  - **Modelo de dominio**: `Claims`, `Identity`, `Principal`, `AuthenticationCredentials`/`AuthenticationResult`, `TokenPair` (`teaf._internal.security.models`) — `SecurityContext` (Sprint 2.2) extendido aditivamente con `identity`/`principal`/`tenant_id`/`provider_id`/`correlation_id`/`request_id`.
  - **Criptografía**: `Argon2PasswordHasher` (por defecto, OWASP) y `BcryptPasswordHasher` (alternativo) implementando `PasswordHasher`; `HmacCryptoProvider` (firmas HMAC-SHA256 con rotación de claves) implementando `CryptoProvider`.
  - **`SecurityMiddleware`**: resuelve identidad en cada petición ("sniffing" de `Authorization: Bearer` hacia `jwt`/`azure-ad` según el `iss` sin verificar, `Basic` hacia `ldap`, `X-API-Key`/`?api_key=` hacia `api-key`), publica el `SecurityContext` en un `ContextVar` — nunca bloquea una petición por falta de autenticación. Publica `authentication.started`/`succeeded`/`failed` vía `EventBus`.
  - **`@authorize()`/`@allow_anonymous()`**: decoradores de autorización declarativa por endpoint (`role=`/`permission=`/`policy=`, funcionan en endpoints síncronos y `async def`) — `teaf._internal.security.decorators`.
  - **Dependencias de FastAPI**: `current_identity`/`current_principal`/`current_claims`/`current_security_context` — leen el `SecurityContext` de la petición en curso vía `Depends(...)`.
  - **`SecurityModule`**: el módulo SDK que empaqueta toda la plataforma (`teaf/_internal/modules/security/`) — segundo módulo real construido sobre el Module SDK (tras `DatabaseModule`), con `SecurityConfiguration`, `SecurityHealth` y 5 capacidades/3 servicios/12 eventos declarados en su manifiesto. No se expone públicamente (mismo criterio que `DatabaseModule`) — una aplicación compone la plataforma directamente vía `teaf.security`.
  - **API pública `teaf.security`** (`teaf/security.py`, 52 símbolos, reexportados también desde `teaf` de nivel superior): `SecurityContext`, `Identity`, `Principal`, `Claims`, `Role`, `Permission`, `Policy`, `IdentityProvider`, `JWTProvider`, `ApiKeyProvider`, `LDAPProvider`, `AzureADProvider`, `AuthenticationProvider`, `AuthorizationProvider`, `PasswordHasher`, `CryptoProvider`, `authorize`, `allow_anonymous`, `current_identity`/`current_principal`/`current_claims`/`current_security_context`, y sus compañeros necesarios (`IdentityProviderRegistry`, `SecurityMiddleware`, resolutores RBAC, tiendas de revocación/API Key, etc.).
  - **Nuevas Settings** (`teaf._internal.config.settings.Settings`): JWT (secret/algorithm/issuer/audience/TTLs/clock skew), API Keys (header/query param/hash secret), LDAP (server/base DN/user DN template/group search), Azure AD (tenant/client id/secret/allowed tenants), Multi Tenant, política de contraseñas (hasher/costes Argon2/rounds BCrypt, reducidos automáticamente en `TestingSettings`), rotación de secretos (activada por defecto en `ProductionSettings`), cabeceras de seguridad HTTP.
  - **8 ejemplos ejecutables** en `examples/`: `jwt-login`, `api-key-auth`, `ldap-login`, `azure-ad-login`, `role-based-endpoint`, `permission-based-endpoint`, `policy-based-endpoint`, `anonymous-endpoint` — todos vía la API pública exclusivamente, verificados por `scripts/check_public_api_boundary.py` y ejecutados como subprocesos reales en `tests/integration/test_teaf_examples.py`.
  - **7 documentos nuevos** en `docs/security/`: `SECURITY-ARCHITECTURE.md`, `JWT.md`, `APIKEY.md`, `LDAP.md`, `AZURE-AD.md`, `RBAC.md`, `CLAIMS.md`. Actualizados: `README.md`, `docs/public-api/PUBLIC-API.md`, `docs/public-api/PACKAGE-STRUCTURE.md`, `docs/public-api/IMPORT-GUIDE.md`, `docs/architecture/ARCHITECTURE.md`, `docs/architecture/MODULE-CATALOG.md`, `docs/standards/SECURITY-STANDARD.md`.
  - **151 pruebas nuevas** (135 de la plataforma de seguridad propiamente dicha, cubriendo modelo de dominio, criptografía, JWT, API Keys, los 5 Identity Providers —LDAP con conexión falsa inyectada, Azure AD con `httpx.MockTransport` y un JWT RS256 real firmado en la prueba—, RBAC/políticas, `SecurityMiddleware` de extremo a extremo, decoradores, dependencias de FastAPI, `SecurityModule`, Settings y la fachada pública; más 16 pruebas que verifican los 8 ejemplos nuevos ejecutándolos como subprocesos reales) — 96% de cobertura de la plataforma de seguridad. Suite completa: 670 pruebas (519 + 151 nuevas).

### Fixed

- `_INFRASTRUCTURE_MODULES` (`teaf/_internal/core/application.py`) registraba un placeholder `"security"` (`CONTRACTS_ONLY`, heredado de Sprint 2.2) en el mismo `ModuleRegistry` que usa `Application(modules=[...])` — colisionaba por nombre con cualquier `SecurityModule` real, impidiendo registrarlo. Retirado, ahora que Sprint 2.7 entrega la implementación real (mismo criterio que ya aplica a `"database"` desde Sprint 2.6).

### Notes

- Compatibilidad hacia atrás completa: ningún símbolo público existente cambia de nombre, firma ni comportamiento. `AuthenticationProvider`/`AuthorizationProvider` (contratos mínimos de Sprint 2.1) se mantienen sin cambios. `SecurityContext` se extiende solo de forma aditiva (todos los campos nuevos con valor por defecto).
- La plataforma está lista para OAuth2 genérico/OIDC genérico/Keycloak/Auth0/Okta/Google/SAML sin rediseño arquitectónico — ver sección 5 de `docs/security/SECURITY-ARCHITECTURE.md`.

## [0.6.3-alpha] - 2026-08-04

### Added

- **Module Registration API** (Sprint 2.6.3, cierre de la serie Sprint 2.6): registrar módulos usando exclusivamente la API pública — sin conocer el `Runtime`, sin llamar a `module.bootstrap()` a mano, sin `asyncio.run()`, sin threads.
  - `Application(modules=[...])`: nuevo parámetro (keyword-only) del constructor — los módulos pasados arrancan automáticamente cuando arranca el ciclo de vida ASGI de la aplicación.
  - `Application.add_module(module) -> Application`: forma encadenable equivalente (`Application().add_module(A()).add_module(B())`).
  - Toda la orquestación vive en el composition root (`teaf/_internal/core/application.py`, `_lifespan`): arranca los módulos pendientes justo después de `runtime.startup()`, en orden de registro, y los apaga en orden inverso antes de `runtime.shutdown()` — el `Runtime` en sí no cambia (mantiene su dependencia de una sola vía hacia `sdk/`, nunca al revés, evitando un ciclo real con `ModuleContext`).
  - Errores existentes (`ModuleRegistrationException` por duplicados, `ModuleValidationException` por manifiestos inválidos) se siguen lanzando igual, ahora disparados por el arranque del ciclo de vida en vez de por una llamada manual — mismo contrato de errores.
  - Nuevo ejemplo `examples/module-registration/` (4º ejemplo de `examples/`): registra un módulo con `Application(modules=[HelloModule()])` y dispara el ciclo de vida con `TestClient`, sin bootstrap manual.
  - 18 pruebas nuevas (`tests/unit/test_module_registration.py`): constructor con 0/1/N módulos, `.add_module()` encadenado, orden de arranque/apagado, integración con `Runtime`/`CapabilityRegistry`, duplicados, manifiestos inválidos, ciclo de vida (`READY`/`DISPOSED`). Suite completa: 519 pruebas.
  - Documentación: nueva sección "Registrar módulos" en `docs/public-api/PUBLIC-API.md`; guía de migración (bootstrap manual → `Application(modules=[...])`) en `docs/public-api/MIGRATION-GUIDE.md`; nota cruzada en `docs/sdk/SDK.md`.

### Notes

- Compatibilidad hacia atrás completa: `Application()` sin argumentos, `create_app(settings)` posicional y todo el resto de la API pública (`Runtime`, `ModuleRegistry`, `CapabilityRegistry`, `ServiceContainer`, `PluginLoader`, `ModuleBase.bootstrap()`/`.shutdown()` manuales) siguen funcionando exactamente igual — ninguna capacidad existente se elimina ni cambia de comportamiento.

## [0.6.2-alpha] - 2026-08-04

### Changed

- **Internal Namespace Refactor** (Sprint 2.6.2): el paquete privado `backend/` (127 archivos, 12 subpaquetes reales más 10 directorios reservados) se mueve íntegramente a `teaf/_internal/`, como subpaquete privado de `teaf` en vez de paquete de nivel superior independiente — elimina por construcción el riesgo de colisión de namespace con un posible paquete `backend/` propio de una aplicación consumidora (resolución de imports dependiente del orden de `sys.path`). La API pública (`from teaf import ...`, los símbolos de `__all__` de `teaf/__init__.py`) no cambia en absoluto — cero cambios requeridos en código consumidor. Ver [ADR-006](docs/architecture/adr/ADR-006-internal-namespace-refactor.md).
  - `pyproject.toml`: `[tool.setuptools.packages.find].include` ya no declara `backend*` — `teaf._internal` se descubre automáticamente como subpaquete de `teaf*`. Mismo ajuste en `[tool.ruff].src` y `[tool.mypy].packages`.
  - `scripts/check_public_api_boundary.py`: generalizado de coincidencia por raíz a coincidencia por **prefijo punteado**, necesario porque `teaf._internal` (a diferencia del antiguo `backend`) es un namespace de dos segmentos que cuelga del propio namespace público `teaf`. `PRIVATE_NAMESPACES` pasa de `("backend",)` a `("teaf._internal",)`. `check_paths()` gana un parámetro `forbidden` opcional.
  - **`scripts/check_internal_namespace.py`** (nuevo): verificador de integridad de la migración — confirma que no queda ningún import de `backend.*`, que `backend/` no existe en disco, y que todo el árbol `teaf.*` sigue siendo importable de punta a punta.
  - 4 pruebas nuevas (`tests/unit/test_internal_namespace.py`): ausencia de `backend` como paquete de nivel superior, `teaf._internal` importable, ningún import de `backend.*` en el repositorio, superficie pública intacta tras el refactor. Suite completa: 499 pruebas (495 + 4 nuevas).
  - Sin cambios funcionales: mismos módulos, mismas clases, mismo comportamiento — únicamente reorganización de namespace y reescritura mecánica de 402 líneas de import en 125 archivos.

## [0.6.1-alpha] - 2026-08-03

### Added

- **API Pública `teaf/`** (Sprint 2.5.1, Public SDK & Packaging): TEAF se instala como un paquete Python profesional (`pip install -e .`) y se consume exclusivamente vía `from teaf import ...` — sin conocer `backend/` por dentro. Sin capacidades nuevas del Runtime, sin módulos nuevos: exclusivamente empaquetado y experiencia de desarrollador sobre lo construido en los Sprints 2.1-2.6.
  - **Catorce símbolos principales** (`teaf/__init__.py`, `__all__` explícito): `Application`, `Runtime`, `Module` (alias de `ModuleBase`), `ModuleBase`, `ModuleBuilder`, `ModuleContext`, `ModuleManifest`, `ServiceContainer`, `EventBus`, `CapabilityRegistry`, `ModuleRegistry`, `Health` (alias de `CapabilityHealth`), `Configuration` (alias de `Settings`), `Version` — más cinco símbolos compañero imprescindibles para usarlos sin recurrir a `backend.*` (`Lifetime`, `Event`, `CapabilityCategory`, `ModuleCategory`, `get_configuration`).
  - **Nueve fachadas** bajo `teaf/` (`application.py`, `runtime.py`, `modules.py`, `services.py`, `events.py`, `configuration.py`, `capabilities.py`, `health.py`, `version.py`), cada una con su propio `__all__`, ninguna importa a otra — todas importan directamente de `backend/` (dirección de dependencias siempre `teaf/ → backend/`, nunca al revés, para evitar un ciclo real con `backend.core.application`).
  - **`Application`**: fachada de aplicación, callable ASGI (`Application()` se sirve directamente con `uvicorn app:app`), con `.runtime`, `.version`, `.asgi` (vía de escape al `FastAPI` subyacente).
  - **`teaf.version`**: único punto de verdad de cinco números de versión independientes — `FRAMEWORK_VERSION`, `SDK_VERSION`, `RUNTIME_VERSION` (nuevo — `backend/runtime/__init__.py`), `MODULE_SPEC_VERSION`, `PUBLIC_API_VERSION` (nuevo, nace en este Sprint) —, la clase `Version` (instancia ya construida, `teaf.Version`) y `is_compatible(actual, constraint)`, una utilidad de comparación de versiones independiente del ciclo de vida de un módulo.
  - **`scripts/check_public_api_boundary.py`**: verificador estático (basado en `ast`, nunca ejecuta el código analizado) de que un árbol de archivos solo importa `teaf`, nunca `backend.*` — sienta la base para una futura verificación en CI, sin estar cableado a ningún pipeline todavía.
  - **`examples/`** (3 ejemplos ejecutables, cada uno con su propio `README.md`): `hello-world/` (ciclo de vida mínimo), `basic-module/` (autoría de un módulo propio), `application-bootstrap/` (una `Application` completa con un módulo registrado) — los tres importan exclusivamente `from teaf import ...`, verificado por el checker de límites y por pruebas dedicadas.
  - **`docs/public-api/`** (5 documentos): `PUBLIC-API.md`, `PACKAGE-STRUCTURE.md`, `IMPORT-GUIDE.md`, `VERSIONING.md`, `MIGRATION-GUIDE.md`.
  - **`pyproject.toml`**: sección `[project]` completa (`name = "teaf"`, versión, clasificadores, `requires-python = ">=3.11"`, dependencias sincronizadas con `requirements.txt`), `[build-system]` (`setuptools`), descubrimiento de paquetes (`teaf*` + `backend*`), `teaf/py.typed` (PEP 561). Sin `[project.scripts]` — sin CLI todavía (ver "NO IMPLEMENTAR").
- 68 pruebas nuevas (494 en total): superficie pública completa (`__all__`, identidad de alias, sin fugas de `backend.*`), cada fachada por separado, un flujo completo de autoría de módulo usando solo `teaf.*` contra un `Runtime` real, el verificador de límites (unitarias + contra `examples/` real), ejecución real de los tres ejemplos como subprocesos, `Application` como ASGI real (`httpx.ASGITransport`), y metadata de empaquetado (`pyproject.toml` ⇄ `requirements.txt` ⇄ distribución instalada). Cobertura del código nuevo de Sprint 2.5.1: 100% (`teaf/`), 98% (`scripts/check_public_api_boundary.py`, solo sin cubrir el bloque `if __name__ == "__main__":`).

### Changed

- Versión del framework: `0.6.0-alpha` → `0.6.1-alpha`. Nota de numeración: este Sprint se planificó como "2.5.1" (una continuación directa de Sprint 2.5/v0.5.0-alpha), pero se implementó después de que Sprint 2.6 ya hubiera publicado v0.6.0-alpha — se usa v0.6.1-alpha (PATCH sobre la versión real vigente) en vez de v0.5.1-alpha para no retroceder el historial de versiones.
- `docs/architecture/MODULE-CATALOG.md`: sin cambios — este Sprint no introduce ni modifica ningún módulo del catálogo.

### Notes

- Sin capacidades nuevas del Runtime, sin módulos nuevos, sin cambios funcionales en `backend/runtime/` ni `backend/sdk/` (la única adición en esas rutas es la constante `RUNTIME_VERSION` en `backend/runtime/__init__.py`, puramente declarativa). `DatabaseModule` (Sprint 2.6) sigue sin cablearse en `create_app()` y sin exponerse desde `teaf/` — sigue siendo opt-in.
- Verificado: `pip install -e .` instala correctamente (`teaf==0.6.1a0` normalizado PEP 440); `import teaf` y cada `from teaf import ...` funcionan; sin dependencias circulares (`teaf/ → backend/` en un solo sentido); el Runtime y el arranque real (`uvicorn`) siguen funcionando sin cambios de comportamiento; los tres ejemplos de `examples/` corren de extremo a extremo importando solo `teaf`.

## [0.6.0-alpha] - 2026-08-03

### Added

- **Database Module** (Sprint 2.6, Enterprise Persistence Foundation): el primer módulo oficial de TEAF construido enteramente sobre el [Module SDK](docs/sdk/SDK.md) (Sprint 2.5) — sin una sola llamada directa a `ServiceContainer`/`CapabilityRegistry`, todo pasa por `ModuleBase.bootstrap()`.
  - **`backend/providers/database/`** (extiende el andamiaje de Sprint 2.2 con implementación real): `engine.py` (`DatabaseDialect` SQLite/PostgreSQL/SQL Server, `create_engine()` async sobre SQLAlchemy 2.x — SQLite con `StaticPool` para bases de datos en memoria), `base_model.py` (`Base` declarativa + `AuditMixin`: `id` UUID, `created_at`/`updated_at`/`deleted_at`), `sqlalchemy_session.py`/`sqlalchemy_provider.py`/`sqlalchemy_factory.py` (implementaciones reales de `DatabaseSession`/`ConnectionManager`/`DatabaseFactory`), `sqlalchemy_repository.py` (`SQLAlchemyRepository`: CRUD genérico, paginación, filtros de igualdad, soft delete — nunca `commit()`, solo `flush()`), `sqlalchemy_unit_of_work.py` (`SQLAlchemyUnitOfWork`/`Factory`: sin commit implícito, rollback automático en excepción).
  - **`backend/modules/database/`** (el módulo SDK): `configuration.py` (`DatabaseConfiguration`, con `from_mapping()`), `health.py` (`DatabaseHealth`: caché síncrona + `refresh()` asíncrono, resuelve el desajuste entre el `ModuleHealth.check` síncrono del SDK y `health_check()` asíncrono del proveedor), `installer.py` (`DatabaseInstaller`: orquesta Alembic vía su API programática, deliberadamente síncrono y nunca invocado desde los hooks async de `DatabaseModule`), `manifest.py` (`build_database_manifest`: 6 capacidades, 3 servicios, 6 claves de configuración, 1 healthcheck, 2 eventos), `module.py` (`DatabaseModule(ModuleBase)`: motor/proveedor/health construidos en `__init__`, antes de que `bootstrap()` llame a `get_manifest()` por primera vez).
  - **Alembic**: `alembic.ini` + `database/migrations/` (entorno async, plantilla, una revisión baseline sin tablas de negocio) — migraciones de infraestructura, sin lógica de negocio.
  - `DatabaseModule` no está cableado en `create_app()` — opt-in, igual que el resto del SDK en Sprint 2.5.
- 73 pruebas nuevas (415 en total): motor/dialectos, modelo base, sesión/proveedor/fábrica, repositorio (incluye la prueba central de que nunca hace `commit()`), Unit of Work (incluye la prueba central de que nunca hace commit implícito), configuración, health, installer (Alembic real sobre `tmp_path`), manifiesto, y una prueba de integración end-to-end que arranca `DatabaseModule` contra un `Runtime` real. Cobertura del código nuevo de Sprint 2.6: 100%.
- `docs/modules/database/` (4 documentos): `DATABASE.md`, `REPOSITORY.md`, `UNIT-OF-WORK.md`, `MIGRATIONS.md`.

### Changed

- Versión del framework: `0.5.0-alpha` → `0.6.0-alpha`.
- `docs/architecture/MODULE-CATALOG.md`: la fila "Database" pasa de `Documentado` a `Implementado` (primer módulo del catálogo con código ejecutable, ver nota introducida en Sprint 2.0) y enlaza a `docs/modules/database/DATABASE.md`.
- `requirements.txt`: se añaden `sqlalchemy[asyncio]==2.0.36`, `alembic==1.14.0`, `aiosqlite==0.20.0`, `asyncpg==0.30.0`.
- `pyproject.toml`: `extend-exclude` de `ruff` incorpora `database/migrations/versions` (revisiones autogeneradas por Alembic, no se ajustan a las reglas de lint del proyecto).

### Notes

- Sin entidades ni tablas de negocio, sin autenticación/autorización, sin Azure, sin IA, sin MCP, sin Scheduler, sin driver SQL Server real (`aioodbc` no instalado, solo la estructura del dialecto), sin Oracle.
- Verificado sin dependencias circulares; `backend/modules/database/` importa de `backend/providers/database/` en un solo sentido; `backend/runtime/`, `backend/sdk/` y `backend/core/application.py::create_app()` no se modificaron en este Sprint — el módulo consume exclusivamente capacidades ya existentes del SDK y del Runtime.

## [0.5.0-alpha] - 2026-08-03

### Added

- **Module SDK** (Sprint 2.5, Developer Platform): paquete nuevo `backend/sdk/`, dependiente de `backend/core/` y `backend/runtime/` (a diferencia de `backend/runtime/`, que nunca depende de `contracts/`/`providers/` — el SDK sí depende del Runtime: es la capa de autoría de alto nivel apoyada en él). Un desarrollador crea un módulo completo heredando únicamente de `ModuleBase`.
  - **Primitivas de descripción**: `ModuleDescriptor` (metadata de autoría, homónimo deliberado de `backend.core.registry.ModuleDescriptor`), `ModuleConfiguration`, `ModuleHealth` (reutiliza `CapabilityHealth`), `ModuleCapability`, `ModuleService`, `ModuleDependency`, `ModuleCategory` (7 valores).
  - **`ModuleManifest`**: compone `ModuleDescriptor` + license/capabilities/dependencies/configuration/services/health_checks/events/runtime_compatibility/sdk_compatibility, con `as_dict()` aplanado.
  - **`ModuleSpecification v1`** (`specification.py`): diez secciones formales (Metadata, Lifecycle, Dependencies, Capabilities, Configuration, Services, Health, Documentation, Packaging, Validation Rules).
  - **`ModuleBuilder`** (`builder.py`): builder fluido — `with_*`/`add_*`/`build()` — única forma probada de construir un `ModuleManifest`.
  - **`ModuleValidator`** (`validator.py`): valida metadata (slug/semver), duplicados (capacidades/servicios/configuración/health checks/dependencias), auto-dependencias y compatibilidad Runtime/SDK; `validate()`, `validate_or_raise()`, `errors_by_section()`.
  - **`ModuleDependencyResolver`** (`dependency_resolver.py`): resuelve orden de inicialización entre varios manifiestos, detecta ciclos (reutilizando `backend.runtime.dependency_graph.DependencyGraph` vía un adaptador estructural), detecta conflictos de versión, construye árboles de dependencias.
  - **`ServiceBinder`/`CapabilityBinder`** (`service_binder.py`, `capability_binder.py`): traducen `ModuleService`/`ModuleCapability` en registros reales contra `Runtime.register_service`/`register_capability` — el autor del módulo nunca llama al `ServiceContainer`/`CapabilityRegistry` directamente.
  - **`ModuleContext`** (`context.py`): envuelve un `Runtime` + configuración + logger con nombre; atajos `.container`, `.capabilities`, `.features`, `.events`.
  - **`ModuleBase`** (`module_base.py`): la única clase de la que hereda un módulo. Siete hooks opcionales, síncronos o asíncronos (`initialize`, `configure`, `register`, `start`, `ready`, `stop`, `dispose`); `bootstrap()`/`shutdown()` orquestan validación, comprobación de compatibilidad, registro en `ModuleRegistry`, enlace automático de servicios/capacidades y ejecución de hooks, avanzando `ModuleLifecycle` en cada paso.
  - **`ModuleLifecycle`/`ModuleLifecycleState`** (`lifecycle.py`): ocho estados (created → initialized → configured → registered → started → ready → stopped → disposed, más `failed` terminal alcanzable desde cualquier punto), con historial y protección contra retrocesos.
  - **`ModuleInspector`** (`inspector.py`): introspección de solo lectura — `describe`/`services`/`capabilities`/`dependencies`/`events`/`configuration`/`health`/`manifest`.
  - **`MODULE_TEMPLATES`/`ModuleScaffolder`** (`templates.py`, `scaffolder.py`): 7 plantillas (Generic, Database, Security, Storage, Integration, AI, MCP), sin código de negocio; `scaffold()` genera un esqueleto en memoria (Python válido), `write_to_disk()` lo materializa como paso explícito — sin CLI.
  - **`ModuleDocumentationGenerator`** (`documentation_generator.py`): genera Markdown a partir de un `ModuleManifest` — solo el servicio, sin escribir archivos.
  - **`ModuleCertification`** (`certification.py`): certifica ocho secciones (Specification, Manifest, Metadata, Capabilities, Dependencies, Version, Health, Documentation) — más estricta que `ModuleValidator` en `documentation` (requerida para certificar, no para registrarse).
  - Cinco excepciones nuevas: `ModuleValidationException`, `ModuleCompatibilityException`, `ModuleDependencyException`, `ModuleRegistrationException`, `ModuleLifecycleException`.
- 130 pruebas nuevas (342 en total): primitivas, manifiesto/especificación, builder, validador, resolutor de dependencias, binders, `ModuleBase`/`ModuleContext` (incluye todos los caminos de fallo y comparador de compatibilidad), inspector, plantillas/scaffolder, generador de documentación, certificación. Cobertura del código nuevo de Sprint 2.5: 100%.
- `docs/sdk/` (6 documentos): `SDK.md`, `MODULE-SPECIFICATION.md`, `MODULE-BUILDER.md`, `MODULE-LIFECYCLE.md`, `MODULE-CERTIFICATION.md`, `DEVELOPER-GUIDE.md`.

### Changed

- Versión del framework: `0.4.0-alpha` → `0.5.0-alpha`.

### Notes

- Sprint 2.5 es exclusivamente infraestructura de autoría: ningún módulo real (Database, Security, AI, ...) se implementa con el SDK todavía — sin CLI, sin generación de proyectos completos, sin persistencia de módulos, sin Database/Security/Storage/Scheduler/OpenTelemetry/Azure/MCP/AI reales.
- Verificado sin dependencias circulares; `backend/sdk/` depende de `backend/core/` y `backend/runtime/` en un solo sentido (ningún archivo de `runtime/`/`core/` importa `sdk/`); el arranque real (`uvicorn`) sigue sirviendo correctamente sin ningún módulo SDK cableado en `application.py` (el SDK es opt-in, no se auto-carga).

## [0.4.0-alpha] - 2026-08-03

### Added

- **Platform Intelligence** (Sprint 2.4): el Runtime gana la capacidad de describirse a sí mismo — extiende, no reemplaza, la infraestructura de Sprint 2.3.
  - **Capability Model** (`backend/runtime/capabilities/`): `CapabilityMetadata` (17 campos), `Capability`, `CapabilityCategory` (13 valores), `CapabilityStatus`, `CapabilityHealth`, `CapabilityBuilder` (fluido) y `CapabilityRegistry` (`register`/`unregister`/`find`/`exists`/`list`/`search`/`describe`). Ninguna capacidad real registrada.
  - `CapabilityProviderRegistry` (`provider_registry.py`): agregación de capacidades de múltiples proveedores vía un `typing.Protocol` estructural (`CapabilityProviderLike`), sin importar `backend/contracts/` — preparación para un futuro servidor MCP, sin implementarlo.
  - **Feature Flags** (`backend/runtime/features/`): `FeatureFlag`, `FeatureManager` (`register`/`enable`/`disable`/`exists`/`is_enabled`/`list`/`describe`), `FeatureGroup` (7 valores: Platform, Security, Database, AI, MCP, Experimental, Infrastructure), `FeatureStatus`. Sin persistencia.
  - `ModuleDescriptor` (`backend/core/registry.py`) gana campos aditivos: `author`, `description`, `lifecycle_state` (nuevo `ModuleLifecycleState`, propio de Core), `capabilities`, `tags`, `documentation`, `experimental`, `created_at`, `updated_at`, propiedad `id` y `as_dict()`; `ModuleRegistry` gana `unregister()`.
  - `Plugin` (`backend/runtime/plugin_loader.py`) gana la propiedad `metadata` (`PluginMetadata`, derivada por defecto de `name`/`version`); `PluginLoader` gana `unload()`.
  - `ServiceContainer` (`backend/runtime/container.py`) gana `ServiceMetadata`, `ServiceHealth`, registro opcional de metadata en `register_singleton`/`register_scoped`/`register_transient`/`register_instance`, `unregister()` y `describe_services()`.
  - `EventBus` (`backend/runtime/event_bus.py`) gana historial acotado (`history_limit`, `history(limit=...)`) — retiene los eventos publicados aunque no haya suscriptores.
  - `ServiceDiscovery` (`backend/runtime/service_discovery.py`): `list`/`search`/`resolve`/`describe`/`capabilities`/`dependency_tree` (con protección contra ciclos) sobre `ServiceContainer`.
  - `RuntimeDiagnostics` (`backend/runtime/diagnostics.py`) y `RuntimeSelfDescription` (`backend/runtime/self_description.py`): las dos fotografías extendidas del estado del Runtime, servidas por `Runtime.diagnostics()`/`Runtime.self_description()`.
  - `Runtime` (`backend/runtime/runtime.py`) gana: atributos compuestos `capability_registry`, `feature_manager`, `capability_provider_registry`, `service_discovery`, `framework_version`, `modules`; wrappers `register_module`/`unregister_module`, `register_service`/`remove_service`/`resolve_service`, `register_capability`/`remove_capability`, `load_plugin`/`unload_plugin`, `enable_feature`/`disable_feature` (cada uno publica su evento correspondiente en el `EventBus`); eventos nuevos `framework.started`/`framework.stopped` (junto a los ya existentes, por compatibilidad), `module.registered`/`module.unregistered`, `service.registered`/`service.removed`/`service.resolved`, `capability.registered`/`capability.removed`, `plugin.loaded`/`plugin.unloaded`, `feature.enabled`/`feature.disabled`.
  - **Runtime API** (`backend/runtime/api.py`, `GET /runtime/*`): `info`, `modules`, `services`, `plugins`, `capabilities`, `features`, `events` (con `?limit=`), `configuration`, `dependencies`, `self` — 10 endpoints, toda la información leída en vivo del Runtime.
  - **Developer API** (`backend/developer/runtime_api.py`, paquete nuevo): `DeveloperRuntimeAPI` — mismas 9 superficies de consulta que la Runtime API (salvo `self`), sin HTTP, reutilizando las funciones `build_*_payload` del router para no duplicar el ensamblado de datos.
  - **Runtime Manifest** (`backend/runtime/manifest.py`): `generate_manifest()`/`write_manifest()` producen `runtime.manifest.json` (Framework, Version, Runtime, Modules, Capabilities, Services, Plugins, Configuration, Feature Flags, Contracts, Providers, Factories) — generado automáticamente al arrancar (excepto en `TESTING`), gitignored.
  - Contratos nuevos en `backend/contracts/`: `CapabilityProvider` y `FrameworkKnowledgeProvider` — preparación para IA/MCP, sin implementación.
  - `backend/core/application.py`: monta `create_runtime_router`, construye `DeveloperRuntimeAPI`, genera `runtime.manifest.json` en `_lifespan` (guardado ante `OSError`), y expone `_configuration_summary()` como fuente única del resumen de configuración no sensible.
- 96 pruebas nuevas (212 en total): Capability Model, Feature Flags, Service Discovery, extensiones de `Runtime` (wrappers + eventos + `diagnostics()`/`self_description()`), Runtime Manifest, Developer API, Runtime API (integración HTTP) y extensiones de `ModuleDescriptor`/`PluginMetadata`/`ServiceMetadata`/`EventBus`. Cobertura del código nuevo de Sprint 2.4: 100%.
- `docs/platform/` (5 documentos): `PLATFORM-INTELLIGENCE.md`, `CAPABILITY-REGISTRY.md`, `RUNTIME-API.md`, `DEVELOPER-API.md`, `SELF-DESCRIBING-RUNTIME.md`.

### Changed

- Versión del framework: `0.3.0-alpha` → `0.4.0-alpha`.
- `.gitignore`: nueva entrada `runtime.manifest.json` (artefacto generado, nunca versionado).

### Notes

- Sprint 2.4 es exclusivamente infraestructura de introspección: ninguna capacidad, feature flag ni plugin real se registra — sin persistencia, sin IA, sin MCP, sin autenticación en la Runtime API todavía.
- Verificado sin dependencias circulares, `backend/runtime/` sigue sin importar `backend/contracts/` ni `backend/providers/` (incluida la nueva preparación para MCP, resuelta con `typing.Protocol` estructural), y el arranque real (`uvicorn`) sirve correctamente los 10 endpoints de `/runtime/*` además de `/info`.

## [0.3.0-alpha] - 2026-08-02

### Added

- **Framework Runtime** (Sprint 2.3): paquete `backend/runtime/`, independiente de `contracts/`/`providers/` (solo depende de `backend/core/`):
  - `ServiceContainer` (`container.py`): resolución por contrato con ciclos de vida Singleton/Scoped/Transient, resolución perezosa (`resolve_lazy`/`Lazy[T]`), factories que resuelven otras dependencias, y detección de dependencias circulares (`CircularDependencyException`).
  - `LifecycleManager` (`lifecycle.py`): cinco etapas (Bootstrap → Startup → Running → Shutdown → Stopped) con hooks síncronos o asíncronos por etapa.
  - `StartupPipeline`/`ShutdownPipeline` (`pipeline.py`): pasos nombrados, FIFO en el arranque y LIFO en el apagado.
  - `ModuleDiscovery` (`discovery.py`): lectura del `ModuleRegistry` con filtro opcional por estado.
  - `DependencyGraph` (`dependency_graph.py`): grafo de dependencias entre módulos con detección de ciclos y orden topológico, verificado antes de correr el `StartupPipeline`.
  - `EventBus` (`event_bus.py`): publicación/suscripción síncrona interna, sin mensajería distribuida.
  - `PluginLoader` (`plugin_loader.py`): contrato `Plugin` mínimo y mecanismo de carga/validación, sin plugins reales.
  - `ConfigurationPipeline` (`configuration_pipeline.py`): validadores de configuración por módulo, ejecutados antes de verificar el grafo de dependencias.
  - `Runtime` (`runtime.py`): orquestador que compone todo lo anterior; conectado al ciclo de vida de FastAPI vía `lifespan` en `backend/core/application.py`.
- `ModuleDescriptor` (`backend/core/registry.py`) gana el campo aditivo `dependencies: tuple[str, ...]` — el módulo `ai` ya declara `("security",)`, reflejando la regla ya fijada en FRAMEWORK-BLUEPRINT.md.
- `GET /info` ampliado con `state`, `lifecycleStage`, `loadedModules` y `registeredCapabilities` del Runtime, leídos en cada petición (no una fotografía capturada al arrancar).
- 60 pruebas nuevas (116 en total): Service Container, Lifecycle, Pipelines, Event Bus, Module Discovery, Dependency Graph, Plugin Loader, Configuration Pipeline y el `Runtime` orquestador — sin integraciones con servicios reales.
- `docs/runtime/RUNTIME.md` documenta la arquitectura del Runtime, el ciclo de vida, el registro de módulos, el contenedor de servicios, el event bus, el plugin loader y las buenas prácticas de extensión.

### Changed

- Versión del framework: `0.2.0-alpha` → `0.3.0-alpha`.
- `backend/core/application.py`: ahora usa `lifespan` de FastAPI para arrancar/apagar el `Runtime`; `/info` recibe un `Callable` que lee el estado del Runtime en vivo en vez del registro estático anterior.

### Notes

- Sprint 2.3 es exclusivamente infraestructura de ejecución: Service Container, ciclo de vida, pipelines, descubrimiento, grafo de dependencias, event bus y plugin loader — sin ninguna implementación ni conexión real (sin PostgreSQL, SQLAlchemy funcional, JWT/OAuth, IA, MCP, scheduler, notificaciones ni storage reales, sin Docker ni Azure).
- Verificado sin dependencias circulares a nivel de archivo y que `backend/core/` (salvo `application.py`, el composition root ya documentado) sigue sin depender de ningún otro módulo del framework.

## [0.2.0-alpha] - 2026-08-02

### Added

- Estructura inicial del monorepo del framework: `backend/`, `frontend/`, `database/`, `docker/`, `scripts/`, `tests/`, `docs/`, `.github/`.
- Documentación base de arquitectura: `docs/architecture/ARCHITECTURE.md` y `docs/architecture/STACK.md`.
- Roadmap del framework con 5 versiones planificadas: `docs/roadmap/ROADMAP.md`.
- Primeros 5 Architecture Decision Records (ADR-001 a ADR-005) sobre FastAPI, PostgreSQL, Docker, API First y Cloud Ready.
- Estándares obligatorios del framework: API, base de datos, código, seguridad y logging (`docs/standards/`).
- Gobernanza de GitHub: `CODEOWNERS`, plantillas de Issues y Pull Request, `CONTRIBUTING.md`.
- Licencia MIT del proyecto.
- `CLAUDE.md`, `/templates/` (9 plantillas reutilizables), estándar de Git (`GIT-STANDARD.md`), backlog inicial (`BACKLOG.md`), catálogo de módulos (`MODULE-CATALOG.md`), quality gates, definition of done y glosario del proyecto.
- Framework Blueprint oficial (`docs/architecture/FRAMEWORK-BLUEPRINT.md`) con 12 diagramas Mermaid (arquitectura por capas, mapa de dependencias, flujos de inicialización/petición/excepción, arquitectura física de despliegue, arquitectura de seguridad, proveedores de IA y MCP) y documentos complementarios `NFR.md`, `DECISION-TREE.md`, `EXTENSIBILITY.md`.
- **Bootstrap ejecutable del framework** (Sprint 2.1): Application Factory (`backend/core/application.py`), configuración por entorno (Development/Testing/Staging/Production), logging estructurado (consola/JSON/archivo con rotación), jerarquía de excepciones (`ApplicationException` y 6 subtipos), middlewares de correlation-id y logging de peticiones, manejo centralizado de errores en formato RFC 7807, rutas de sistema (`/`, `/health`, `/live`, `/ready`), utilidades genéricas en `shared/`, y suite de pruebas base (`tests/unit/`, `tests/integration/`). Documentado en `docs/core/CORE.md`.
- Manifiestos de dependencias del backend (`requirements.txt`, `requirements-dev.txt`) y configuración de herramientas (`pyproject.toml`: ruff, black, mypy, pytest).
- **Infrastructure Foundation** (Sprint 2.2): paquete `backend/contracts/` con 9 interfaces puras (Repository, UnitOfWork, DatabaseProvider, Authentication/AuthorizationProvider, TelemetryProvider, StorageProvider, AIProvider, SchedulerProvider, NotificationProvider); paquete `backend/providers/` con clases base y factories abstractas para database (`DatabaseFactory`, `DatabaseSession`, `ConnectionManager`, `RepositoryBase`), security (`SecurityContext`, `AuthenticationManager`, `AuthorizationManager`, RBAC, `SecurityFactory`), telemetry (`TracerProvider`, `MetricsProvider`, `LoggerProvider`, `TelemetryContext`), storage y ai; `ModuleRegistry` (`backend/core/registry.py`) registrado por instancia de aplicación (no como singleton de proceso); expansión de la inyección de dependencias (`backend/providers/dependencies.py`); nueva ruta `/info` con versión y estado de los módulos registrados. Documentado en `docs/infrastructure/INFRASTRUCTURE.md`. 32 pruebas nuevas (contracts, registry, factories, DI) — sin integraciones reales.

### Changed

- `README.md`: la sección "Cómo iniciar el proyecto" ahora documenta pasos reales de arranque (`uvicorn backend.main:app --reload`), en vez de la nota de "sin código ejecutable" de la iteración de fundación.
- Versión del framework (`FRAMEWORK_VERSION` en `backend/core/application.py`, expuesta en `/health` y `/info`): `0.1.0` → `0.2.0-alpha`.

### Notes

- El backend ya es ejecutable end-to-end (`uvicorn backend.main:app --reload` responde en `/`, `/health`, `/live`, `/ready`, `/info`). Sigue sin haber base de datos, autenticación, frontend ejecutable, Docker ni CI/CD reales — llegan en Sprints posteriores (ver `docs/roadmap/ROADMAP.md`, Versión 1 en adelante).
- Sprint 2.2 es exclusivamente infraestructura abstracta: contratos y clases base, sin ninguna implementación ni conexión real (sin PostgreSQL, SQLAlchemy funcional, JWT/OAuth, IA, MCP, storage ni scheduler reales).

[Unreleased]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.5.0-alpha...HEAD
[0.5.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.4.0-alpha...v0.5.0-alpha
[0.4.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.3.0-alpha...v0.4.0-alpha
[0.3.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.2.0-alpha...v0.3.0-alpha
[0.2.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/main...v0.2.0-alpha
