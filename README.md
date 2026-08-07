# TEAF — TORUS Enterprise Application Framework

> Framework empresarial base para el desarrollo de aplicaciones de TORUS. No es una aplicación: es la plataforma sobre la que se construyen todas las aplicaciones.

[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-yellow.svg)](LICENSE)
[![Estado](https://img.shields.io/badge/Estado-En%20construcci%C3%B3n-blue.svg)](docs/roadmap/ROADMAP.md)

---

## Qué es TEAF

**TEAF (TORUS Enterprise Application Framework)** es el framework empresarial interno de TORUS. Su propósito es el mismo que cumplen Spring Boot en el ecosistema Java o .NET Boilerplate en el ecosistema .NET, pero diseñado y especializado para las necesidades de nuestra organización: un conjunto de capas, convenciones, patrones y estándares reutilizables sobre los cuales se construyen todas las aplicaciones empresariales futuras.

TEAF **no es una aplicación de negocio**. Es la base arquitectónica — backend, frontend, base de datos, contenedores, observabilidad, seguridad y estándares — que evita que cada nueva aplicación tenga que reinventar su propia infraestructura, sus propios patrones de acceso a datos o su propia estrategia de seguridad.

Aplicaciones que se construirán en el futuro sobre TEAF (fuera del alcance de este repositorio):

- TicketGateway
- Portal TORUS
- Portal NOC
- Portal SRE
- Inventario TI
- Gestor de Incidentes
- Dashboards empresariales
- Automatizaciones
- Integraciones SAP, Salesforce y Control-M
- IA Empresarial

## Objetivos

1. **Reutilización**: eliminar la duplicación de infraestructura y patrones entre aplicaciones.
2. **Consistencia**: todas las aplicaciones TORUS comparten arquitectura, convenciones y estándares.
3. **Velocidad**: reducir drásticamente el tiempo de arranque de un nuevo proyecto.
4. **Calidad**: imponer buenas prácticas (Clean Architecture, SOLID, DDD) desde el primer commit.
5. **Preparación para la nube**: despliegue nativo en contenedores, listo para Azure.
6. **Preparación para IA**: capas de abstracción para integrar modelos de lenguaje y automatización inteligente sin acoplar el negocio a un proveedor concreto.
7. **Observabilidad**: trazabilidad y monitoreo de extremo a extremo desde el día uno.
8. **Mantenibilidad a largo plazo**: una base que pueda evolucionar de forma segura durante varios años y ser comprendida y mantenida tanto por humanos como por asistentes de IA.

## Arquitectura

TEAF se organiza como una arquitectura limpia en capas (Clean Architecture + DDD), con separación estricta de responsabilidades entre la capa de API, la capa de servicios/aplicación, la capa de dominio y la capa de infraestructura/persistencia. El detalle completo — capas, principios, flujo de datos y diagramas — está documentado en:

📄 **[docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)**

### Principios arquitectónicos

| Principio | Descripción |
|---|---|
| API First | Todo se diseña primero como contrato de API, antes que como implementación. |
| Cloud Ready | Diseñado para ejecutarse en la nube desde el primer día. |
| Docker First | Todo componente se ejecuta y se distribuye en contenedores. |
| AI Ready | Abstracciones nativas para integrar IA sin acoplamiento. |
| Security by Design | La seguridad se diseña, no se añade después. |
| Observability First | Trazas, métricas y logs desde el diseño inicial. |
| Database Agnostic | El dominio no depende de un motor de base de datos concreto. |
| Configuration by Environment | La configuración varía por entorno, nunca por código. |
| Modular Architecture | Módulos desacoplados y con límites claros. |
| Clean Architecture | Independencia del dominio respecto a frameworks y detalles técnicos. |
| Dependency Injection | Las dependencias se inyectan, nunca se instancian directamente. |
| Repository Pattern | Acceso a datos abstraído detrás de interfaces. |
| Service Layer | La lógica de aplicación vive en servicios, no en controladores. |
| SOLID / DRY / KISS | Principios de diseño de software aplicados de forma consistente. |

## Tecnologías

| Categoría | Tecnología |
|---|---|
| Backend | FastAPI |
| Frontend | React + TypeScript |
| Base de datos | PostgreSQL |
| ORM | SQLAlchemy |
| Migraciones | Alembic |
| Contenedores | Docker |
| CI/CD | GitHub Actions |
| Hosting POC | Render |
| Producción | Azure App Service |
| Observabilidad | OpenTelemetry |
| Autenticación | JWT |
| UI | Material UI |

La justificación de cada elección tecnológica está documentada en **[docs/architecture/STACK.md](docs/architecture/STACK.md)**.

## Estructura del repositorio

```
/
├── teaf/             # API pública (from teaf import ...) + teaf/_internal/ (implementación
│                      # privada: API, capas de servicio, repositorio, dominio e infraestructura, FastAPI)
├── frontend/        # Aplicación React + TypeScript + Material UI
├── database/        # Migraciones (Alembic) y datos semilla
├── docker/           # Definiciones de contenedores por componente
├── scripts/          # Automatización: setup, lint, migraciones, despliegue
├── tests/            # Pruebas unitarias, de integración y end-to-end
├── docs/             # Documentación de arquitectura, estándares, ADRs y roadmap
└── .github/          # Plantillas de Issues/PR, CODEOWNERS y CI/CD
```

Cada carpeta de código incluye un `README.md` que documenta su responsabilidad dentro de la arquitectura.

## Roadmap

TEAF se construye de forma incremental en cinco versiones, desde la fundación del framework hasta el hardening empresarial completo. Resumen:

| Versión | Enfoque |
|---|---|
| V1 — Foundation | Bootstrap ejecutable del backend/frontend, configuración, base de datos, CI |
| V2 — Core Services | Seguridad (JWT/RBAC), observabilidad real, middlewares, migraciones |
| V3 — Frontend Foundation | Shell de aplicación React, theming, autenticación, cliente API |
| V4 — Integration & AI Ready | Abstracciones de IA, webhooks, scheduler, conectores SAP/Salesforce/Control-M |
| V5 — Enterprise Hardening & Cloud | Despliegue en Azure, hardening de seguridad, CLI de generación de proyectos |

Detalle completo en **[docs/roadmap/ROADMAP.md](docs/roadmap/ROADMAP.md)**.

## Cómo iniciar el proyecto

> **Estado actual: v0.9.1-alpha — bootstrap + infraestructura + Runtime + Platform Intelligence + Module SDK + Database Module + API Pública + Internal Namespace Refactor + Module Registration API + Enterprise Security Platform + Enterprise Observability Platform + Enterprise API Protection Platform (Sprint 2.9).** El backend arranca de extremo a extremo (configuración, logging, middlewares, health checks), tiene un Runtime real ejecutando ciclo de vida, contenedor de servicios, pipelines y grafo de dependencias, puede describirse a sí mismo vía `GET /runtime/*` y un Developer API en proceso, ofrece el SDK oficial para construir módulos (`teaf/_internal/sdk/`) y cuatro módulos reales construidos sobre él (Database Module, Security Module, Observability Module y API Protection Module), y se instala como un **paquete Python profesional**: `pip install -e .` y `from teaf import Application, Module, ModuleBuilder, ...` — la única API pública soportada, sin conocer `teaf/_internal/` por dentro (ver [docs/public-api/](docs/public-api/) y [`examples/`](examples/)). Registrar módulos propios no requiere conocer el `Runtime`: `Application(modules=[TaskModule()])` los arranca automáticamente (ver [PUBLIC-API.md, sección 3](docs/public-api/PUBLIC-API.md#3-registrar-módulos-module-registration-api-sprint-263)). La plataforma de seguridad empresarial (`from teaf.security import ...`) cubre autenticación pluggable (Anonymous/JWT/API Key/LDAP/Azure AD, vía el contrato `IdentityProvider`), RBAC, políticas y hashing de contraseñas (Argon2id/BCrypt) — ver [docs/security/SECURITY-ARCHITECTURE.md](docs/security/SECURITY-ARCHITECTURE.md). La plataforma de observabilidad empresarial (`from teaf.observability import ...`) cubre logging estructurado, tracing distribuido, métricas y health checks compuestos sobre OpenTelemetry, con exportadores Console/OTLP/Prometheus — ver [docs/observability/OBSERVABILITY.md](docs/observability/OBSERVABILITY.md). La plataforma de protección de APIs (`from teaf.api import ...`) cubre rate limiting (cuatro algoritmos, seis dimensiones), cuotas de consumo, CORS, versionado, validación de borde, compresión, idempotencia y auditoría, componibles con una sola llamada (`ApiGateway.install(app)`) — ver [docs/api/API-PROTECTION.md](docs/api/API-PROTECTION.md). El Sprint 2.9.1 endureció todo lo anterior sin añadir funcionalidad: arranque **5,5× más rápido**, una fuga de memoria corregida, `mypy --strict` sin errores, 10 puertas de calidad en **un solo comando** (`python scripts/quality_gates.py`), suites de [benchmarks](benchmarks/README.md) y [pruebas de carga](loadtests/README.md), y compatibilidad hacia atrás verificada de forma mecánica — ver [docs/PRODUCTION-READINESS.md](docs/PRODUCTION-READINESS.md) para el estado real frente a producción, incluidos los hallazgos de seguridad **abiertos**. Ver `docs/roadmap/ROADMAP.md` para lo que llega en cada versión siguiente.

```bash
git clone https://github.com/jesuscampam/torus-enterprise-framework.git
cd torus-enterprise-framework

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env
python -c "from teaf import Application; open('app.py', 'w').write('from teaf import Application\n\napp = Application()\n')"
uvicorn app:app --reload
```

Verifica que responde: `curl http://localhost:8000/health` y `curl http://localhost:8000/info` (versión y módulos registrados). Documentación interactiva (Swagger) en `http://localhost:8000/docs`.

Ejecutar la suite de pruebas: `python -m pytest`.

Para profundizar:

1. **[docs/core/CORE.md](docs/core/CORE.md)** explica la arquitectura del Core implementado y cómo extenderlo — el entry point público es `from teaf import Application; app = Application()` (ver [`teaf/application.py`](teaf/application.py)).
2. **[docs/infrastructure/INFRASTRUCTURE.md](docs/infrastructure/INFRASTRUCTURE.md)** explica los contratos, providers, el registro de módulos y cómo se conectará una implementación real en el futuro.
3. **[docs/runtime/RUNTIME.md](docs/runtime/RUNTIME.md)** explica el ciclo de vida, el contenedor de servicios, los pipelines, el grafo de dependencias, el event bus y el plugin loader.
4. **[docs/architecture/FRAMEWORK-BLUEPRINT.md](docs/architecture/FRAMEWORK-BLUEPRINT.md)** es la arquitectura técnica oficial completa, con diagramas.
5. **[docs/standards/](docs/standards/)** contiene las convenciones obligatorias de API, base de datos, código, seguridad y logging.
6. Los **[ADR](docs/architecture/adr/)** explican el porqué de cada decisión estructural.
7. Recorre `teaf/_internal/` y `frontend/` — cada subcarpeta documenta, en su propio `README.md`, su responsabilidad dentro de la arquitectura.
8. **[docs/public-api/](docs/public-api/)** explica la API pública instalable (`pip install -e .`, `from teaf import ...`, cómo registrar módulos con `Application(modules=[...])`) y los cuatro ejemplos ejecutables de **[`examples/`](examples/)**.

## Contribuir

Antes de contribuir, lee **[CONTRIBUTING.md](CONTRIBUTING.md)** y los estándares en `docs/standards/`.

## Licencia

Este proyecto se distribuye bajo licencia [MIT](LICENSE).
