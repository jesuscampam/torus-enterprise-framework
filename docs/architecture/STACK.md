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

## UI — Material UI

**Por qué**: sistema de diseño maduro y accesible por defecto, con amplia cobertura de componentes empresariales (tablas, formularios, navegación), personalizable vía theming (`frontend/src/theme/`) para mantener identidad visual consistente entre todas las aplicaciones TORUS.

**Alternativas consideradas**: Ant Design (estética menos alineada con el branding deseado), Chakra UI (ecosistema y comunidad menores para componentes empresariales complejos como grids de datos).

**Trade-offs aceptados**: cierto peso adicional en el bundle; mitigado con carga diferida (code-splitting) a nivel de `pages/`.
