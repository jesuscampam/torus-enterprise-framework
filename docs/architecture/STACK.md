# Stack Tecnológico de TEAF

Este documento justifica cada elección tecnológica oficial del framework: por qué fue seleccionada, qué alternativas se consideraron y qué trade-offs se aceptan conscientemente. Los cambios a este stack requieren un ADR (ver [adr/](adr/)).

---

## Backend — FastAPI

**Por qué**: rendimiento asíncrono nativo (ASGI), tipado fuerte con Python type hints, generación automática de contratos OpenAPI (alineado con el principio API First), y validación de datos de primera clase vía Pydantic — el mismo mecanismo que usamos para `schemas/`.

**Alternativas consideradas**: Django REST Framework (más pesado, orientado a monolito con ORM propio, peor ajuste con Clean Architecture y async), Flask (requiere ensamblar manualmente validación, async y documentación OpenAPI).

**Trade-offs aceptados**: ecosistema más joven que Django; requiere disciplina propia del equipo para no acoplar lógica de negocio a los routers (mitigado por el principio Service Layer).

## Frontend — React + TypeScript

**Por qué**: ecosistema maduro, tipado estático que reduce errores en tiempo de compilación, gran disponibilidad de talento, y compatibilidad natural con Material UI para una experiencia visual consistente entre todas las aplicaciones TORUS.

**Alternativas consideradas**: Angular (más opinado y con curva de entrada más alta para equipos pequeños), Vue (ecosistema menor en el contexto de la organización).

**Trade-offs aceptados**: mayor responsabilidad del equipo en decisiones de arquitectura frontend (routing, estado) frente a frameworks más opinados como Angular; se mitiga fijando convenciones propias en `docs/standards/CODING-STANDARD.md`.

## Base de datos — PostgreSQL

**Por qué**: motor relacional open-source robusto, con soporte avanzado de tipos (JSONB, UUID, arrays), extensiones para IA (`pgvector`), transacciones ACID completas, y compatibilidad con Azure Database for PostgreSQL para producción.

**Alternativas consideradas**: MySQL (menor soporte de tipos avanzados y extensiones), SQL Server (coste de licenciamiento y menor alineación con Cloud Ready / Database Agnostic en entornos multi-nube).

**Trade-offs aceptados**: el principio Database Agnostic exige que el dominio no dependa de características exclusivas de PostgreSQL más allá de lo encapsulado en `repository/` y `database/`.

## ORM — SQLAlchemy

**Por qué**: el ORM Python más maduro, con soporte completo de Core (SQL explícito cuando se necesita) y ORM declarativo, y perfecta integración con Alembic para migraciones. Encaja naturalmente con el Repository Pattern: las implementaciones concretas de `repository/` usan SQLAlchemy sin filtrar detalles a `services/`.

**Alternativas consideradas**: Tortoise ORM (más joven, ecosistema menor), tipo activo-record vs. patrón unit-of-work (SQLAlchemy ofrece ambos, elegimos unit-of-work por alinearse mejor con Clean Architecture).

**Trade-offs aceptados**: curva de aprendizaje mayor que ORMs más simples; se mitiga con convenciones estrictas en `DATABASE-STANDARD.md`.

## Migraciones — Alembic

**Por qué**: herramienta oficial del ecosistema SQLAlchemy, migraciones versionadas y reproducibles, soporte de autogeneración a partir de los modelos declarativos.

**Alternativas consideradas**: migraciones manuales en SQL puro (no versionadas de forma consistente, mayor riesgo humano).

**Trade-offs aceptados**: requiere disciplina de revisión manual de las migraciones autogeneradas antes de aplicarlas (ver `DATABASE-STANDARD.md`).

## Contenedores — Docker

**Por qué**: paridad exacta entre entorno local, POC (Render) y producción (Azure App Service); aísla dependencias del sistema operativo host; es el estándar de facto de la industria para Cloud Ready / Docker First.

**Alternativas consideradas**: entornos virtuales sin contenedores (no garantizan paridad entre entornos, mayor riesgo de "funciona en mi máquina").

**Trade-offs aceptados**: overhead operativo de mantener Dockerfiles e imágenes optimizadas; se compensa con la reducción de incidentes de entorno.

## CI/CD — GitHub Actions

**Por qué**: integrado de forma nativa con el repositorio en GitHub, sin infraestructura adicional que operar, con un ecosistema amplio de acciones reutilizables para lint, test, build y despliegue a Azure.

**Alternativas consideradas**: Jenkins (requiere infraestructura propia a mantener), Azure DevOps Pipelines (redundante teniendo el código ya en GitHub).

**Trade-offs aceptados**: dependencia de la disponibilidad de GitHub como plataforma; aceptable dado que el código ya reside allí.

## Hosting POC — Render

**Por qué**: despliegue rápido y de bajo coste para validar aplicaciones construidas sobre TEAF antes de invertir en infraestructura Azure, con soporte nativo de Docker y bases de datos PostgreSQL gestionadas.

**Alternativas consideradas**: entornos locales compartidos (no accesibles para validación con stakeholders), despliegue directo en Azure desde el día uno (mayor coste y fricción para prototipos descartables).

**Trade-offs aceptados**: Render no es el destino final; toda configuración específica de Render debe mantenerse aislada en `docker/` y `config/` para no filtrarse a la lógica de negocio.

## Producción — Azure App Service

**Por qué**: alineado con la infraestructura y los acuerdos empresariales existentes de TORUS, soporte nativo de contenedores Docker, integración con Azure Key Vault (gestión de secretos), Azure Database for PostgreSQL, y Azure Monitor (compatible con OpenTelemetry).

**Alternativas consideradas**: AWS / GCP (fuera del acuerdo empresarial vigente de la organización), Kubernetes autogestionado (complejidad operativa innecesaria para el volumen actual de aplicaciones).

**Trade-offs aceptados**: cierto grado de acoplamiento a servicios gestionados de Azure; mitigado manteniendo Docker First como principio, lo que permite portar los mismos contenedores a otra nube si fuera necesario.

## Observabilidad — OpenTelemetry

**Por qué**: estándar abierto y neutral de proveedor para trazas, métricas y logs; evita el vendor lock-in con una herramienta de observabilidad concreta y es compatible tanto con Azure Monitor como con soluciones open-source (Grafana, Jaeger).

**Alternativas consideradas**: SDKs propietarios de APM (Datadog, New Relic) — descartados por coste y por acoplar la observabilidad a un proveedor específico, en contra del principio Observability First entendido como "instrumentar una vez, exportar a cualquier backend".

**Trade-offs aceptados**: mayor esfuerzo inicial de instrumentación manual frente a agentes "todo incluido" de APM comerciales.

## Autenticación — JWT

**Por qué**: estándar sin estado (stateless), ideal para arquitecturas Cloud Ready con múltiples instancias horizontalmente escalables sin sesión compartida; interoperable entre backend, frontend y futuras integraciones (SAP, Salesforce, Control-M).

**Alternativas consideradas**: sesiones de servidor con estado (requieren almacenamiento compartido y complican el escalado horizontal, en contra de Cloud Ready).

**Trade-offs aceptados**: la revocación de tokens requiere una estrategia explícita (expiración corta + refresh tokens), documentada en `SECURITY-STANDARD.md`.

**Librería — PyJWT** (Sprint 2.7, ver [ADR-007](adr/ADR-007-enterprise-security-stack.md)): implementación de referencia del estándar (RFC 7519), soporta HS256 y RS256/ES256 (extra `[crypto]`, necesario para validar tokens firmados por Azure AD/Entra ID sin gestionar la criptografía a mano), API mínima y estable.

**Alternativas consideradas**: `python-jose` (API más amplia pero menos mantenida activamente; superficie de ataque mayor sin beneficio adicional para el caso de uso de TEAF).

## Identidad — Identity Providers (Sprint 2.7)

**Por qué**: la plataforma de seguridad se diseña alrededor de un contrato `IdentityProvider` (no alrededor de JWT en sí) — JWT es uno de varios mecanismos de identidad, no el único. Esto permite añadir OAuth2/OIDC genérico, Keycloak, Auth0, Okta, Google, GitHub, SAML como implementaciones nuevas sin tocar el Runtime, el `ServiceContainer` ni el `SecurityMiddleware` — ver [ADR-007](adr/ADR-007-enterprise-security-stack.md) y [docs/security/SECURITY-ARCHITECTURE.md](../security/SECURITY-ARCHITECTURE.md).

**Alternativas consideradas**: acoplar la plataforma directamente a JWT (más simple a corto plazo, pero exige un rediseño estructural en cuanto una aplicación TORUS necesite LDAP/Active Directory o Microsoft Entra ID — un requisito ya confirmado, no hipotético).

**Trade-offs aceptados**: una capa de indirección adicional (`IdentityProvider` → `AuthenticationResult` → `SecurityContext`) frente a decodificar un JWT directamente en el middleware.

## LDAP / Active Directory — ldap3

**Por qué**: cliente LDAP puro Python (sin enlazar contra `libldap` del sistema operativo como exige `python-ldap`), lo que preserva Docker First / Cloud Ready (imagen de contenedor sin dependencias nativas adicionales que instalar/mantener); soporta bind simple, búsqueda de grupos y TLS.

**Alternativas consideradas**: `python-ldap` (requiere `libldap2-dev` en la imagen Docker — overhead operativo contrario a Cloud Ready, ver ADR-005).

**Trade-offs aceptados**: `ldap3` es síncrono — las llamadas se ejecutan en threadpool (`anyio.to_thread`) para no bloquear el event loop, mismo patrón que cualquier librería síncrona consumida desde código async.

## Cliente HTTP para OIDC/OAuth2 — httpx

**Por qué**: ya es una dependencia del proyecto (usada en tests desde Sprint 2.1); promovida a dependencia de runtime en Sprint 2.7 porque `AzureADIdentityProvider`/`OpenIDConnectIdentityProvider` necesitan hacer descubrimiento OIDC (`.well-known/openid-configuration`), obtener JWKS y ejecutar el intercambio de código por token del Authorization Code Flow — todo async-nativo, coherente con el resto del framework.

**Alternativas consideradas**: `requests` (síncrono, requeriría el mismo threadpool wrapping que se evita usando `httpx`).

## Contraseñas — Argon2id (vía `argon2-cffi`), BCrypt como proveedor alternativo

**Por qué**: Argon2id es el ganador de la Password Hashing Competition y la recomendación actual de OWASP; resistente a ataques por GPU/ASIC. `PasswordHasher` es un contrato (`teaf._internal.security.crypto.password_hasher.PasswordHasher`) — Argon2 es el proveedor por defecto, BCrypt (vía `bcrypt`) queda disponible como proveedor alternativo sin cambiar el contrato, para compatibilidad con hashes preexistentes de una aplicación migrada a TEAF.

**Alternativas consideradas**: SHA-256/MD5 sin *salt* ni factor de coste (prohibido explícitamente por `SECURITY-STANDARD.md`, vulnerable a fuerza bruta con hardware moderno).

**Trade-offs aceptados**: Argon2 consume más CPU/memoria por diseño (esa es la propiedad de seguridad deseada) — se configura el coste vía `Settings` para poder ajustarlo por entorno.

## UI — Material UI

**Por qué**: sistema de diseño maduro y accesible por defecto, con amplia cobertura de componentes empresariales (tablas, formularios, navegación), personalizable vía theming (`frontend/src/theme/`) para mantener identidad visual consistente entre todas las aplicaciones TORUS.

**Alternativas consideradas**: Ant Design (estética menos alineada con el branding deseado), Chakra UI (ecosistema y comunidad menores para componentes empresariales complejos como grids de datos).

**Trade-offs aceptados**: cierto peso adicional en el bundle; mitigado con carga diferida (code-splitting) a nivel de `pages/`.
