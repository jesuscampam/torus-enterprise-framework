# Arquitectura de TEAF

## 1. Objetivos

La arquitectura de TEAF existe para que cualquier aplicación construida sobre el framework (TicketGateway, Portal TORUS, Portal NOC, Portal SRE, Inventario TI, integraciones SAP/Salesforce/Control-M, IA Empresarial, etc.) herede automáticamente:

- Una separación de responsabilidades clara y verificable.
- Independencia del dominio respecto a frameworks, bases de datos y proveedores externos.
- Seguridad, observabilidad y configuración por entorno resueltas de forma transversal, sin que cada aplicación deba reimplementarlas.
- Preparación nativa para integrar Inteligencia Artificial sin acoplar el dominio a un proveedor de modelos concreto.
- Una base que un equipo humano o un agente de IA puedan mantener y extender con seguridad durante años, sin degradar la coherencia arquitectónica.

## 2. Principios arquitectónicos

| # | Principio | Qué garantiza |
|---|---|---|
| 1 | **API First** | El contrato de la API (OpenAPI) se diseña antes que la implementación; el contrato es la fuente de verdad. |
| 2 | **Cloud Ready** | Ninguna capa asume estado en disco local ni una única instancia; todo componente es horizontalmente escalable. |
| 3 | **Docker First** | Todo servicio se ejecuta, prueba y distribuye como contenedor, idéntico en local, POC y producción. |
| 4 | **AI Ready** | Existe una capa (`ai/`) que abstrae proveedores de LLM, embeddings y vector stores detrás de interfaces estables. |
| 5 | **Security by Design** | Autenticación, autorización y validación de entradas son transversales (`security/`, `middleware/`), no opcionales por endpoint. |
| 6 | **Observability First** | Toda petición es trazable de extremo a extremo (`monitoring/`, OpenTelemetry) desde el primer commit funcional. |
| 7 | **Database Agnostic** | El dominio y los servicios no conocen el motor de base de datos; solo el `repository/` habla SQL/ORM. |
| 8 | **Configuration by Environment** | Ningún valor de entorno (credenciales, endpoints, flags) vive en código; todo se resuelve vía `config/`. |
| 9 | **Modular Architecture** | Cada capa es un módulo con un límite y una responsabilidad únicos, sin dependencias circulares. |
| 10 | **Clean Architecture** | Las dependencias siempre apuntan hacia adentro: `api → services → repository → database`, nunca al revés. |
| 11 | **Dependency Injection** | Las dependencias concretas se inyectan (vía `core/`), nunca se instancian dentro de la lógica de negocio. |
| 12 | **Repository Pattern** | El acceso a datos se abstrae detrás de interfaces (`repository/`), intercambiables sin tocar `services/`. |
| 13 | **Service Layer** | Los casos de uso y la orquestación de negocio viven en `services/`, no en los controladores de `api/`. |
| 14 | **SOLID / DRY / KISS** | Guían cada decisión de diseño de código en todas las capas. |

## 3. Arquitectura en capas

TEAF aplica Clean Architecture con Domain-Driven Design ligero. Las flechas indican dirección de dependencia (siempre hacia el centro):

```
                        ┌─────────────────────────────┐
                        │        Cliente (HTTP)        │
                        └───────────────┬───────────────┘
                                        │
                        ┌───────────────▼───────────────┐
                        │   middleware/  (transversal)   │  correlation-id, auth, logging, rate-limit
                        └───────────────┬───────────────┘
                                        │
                        ┌───────────────▼───────────────┐
                        │        api/  (interfaz)        │  routers, versionado, schemas de E/S
                        └───────────────┬───────────────┘
                                        │  usa
                        ┌───────────────▼───────────────┐
                        │     services/  (aplicación)    │  casos de uso, orquestación, reglas de negocio
                        └───────────────┬───────────────┘
                                        │  usa (vía interfaz)
                        ┌───────────────▼───────────────┐
                        │    repository/  (dominio)      │  contratos de acceso a datos
                        └───────────────┬───────────────┘
                                        │  implementado por
                        ┌───────────────▼───────────────┐
                        │  database/ + models/ (infra)   │  SQLAlchemy, PostgreSQL
                        └─────────────────────────────────┘

  Transversales a todas las capas: core/ · config/ · security/ · monitoring/ · shared/ · ai/ · webhooks/ · scheduler/
```

### Descripción de cada capa (`teaf/_internal/`)

| Capa | Responsabilidad | No debe contener |
|---|---|---|
| `api/` | Exponer contratos HTTP versionados (routers/controladores), (de)serialización vía `schemas/`. | Lógica de negocio ni acceso directo a datos. |
| `core/` | Kernel del framework: bootstrap de la aplicación, contenedor de inyección de dependencias, excepciones base, ciclo de vida. | Reglas de negocio específicas de una aplicación. |
| `services/` | Casos de uso de aplicación: orquesta repositorios, aplica reglas de negocio, coordina transacciones. | SQL, detalles HTTP, detalles de framework web. |
| `repository/` | Contratos (interfaces) e implementaciones de acceso a datos — Repository Pattern. | Lógica de negocio. |
| `database/` | Motor y sesión de SQLAlchemy, `Base` declarativa, gestión del ciclo de conexión. | Reglas de negocio ni entidades de dominio puras. |
| `models/` | Entidades ORM (capa de persistencia). | Lógica de aplicación. |
| `schemas/` | DTOs Pydantic — contratos de entrada/salida de la API, independientes de los modelos ORM. | Acceso a datos. |
| `security/` | Autenticación (JWT), autorización (RBAC), hashing, políticas de permisos. | Lógica de negocio no relacionada con seguridad. |
| `middleware/` | Componentes transversales HTTP: correlation-id, logging de requests, rate limiting, manejo centralizado de errores. | Casos de uso de negocio. |
| `monitoring/` | Observabilidad: instrumentación OpenTelemetry, métricas, health checks. | Lógica de negocio. |
| `shared/` | Utilidades, constantes y tipos genéricos reutilizables entre capas. | Dependencias hacia capas superiores (`api`, `services`). |
| `config/` | Configuración tipada por entorno (dev/staging/prod), carga de secretos. | Valores hardcodeados de negocio. |
| `ai/` | Abstracciones AI-Ready: interfaces de cliente LLM, prompts, embeddings, vector stores. | Acoplamiento directo a un proveedor de IA concreto en las capas superiores. |
| `webhooks/` | Framework para recepción/emisión de eventos externos (SAP, Salesforce, Control-M). | Lógica de negocio específica de una integración concreta. |
| `scheduler/` | Framework de tareas programadas y trabajos en background. | Lógica de negocio de una aplicación específica. |

### Frontend

El frontend replica el mismo espíritu de separación de responsabilidades: `pages/` (vistas), `components/` (UI reutilizable), `services/` (cliente API tipado), `hooks/`, `store/` (estado), `types/`, `utils/`, `theme/` (Material UI) y `config/` (configuración por entorno). El frontend nunca accede a la base de datos ni conoce detalles de infraestructura del backend; solo consume contratos de `api/` vía `frontend/src/services/`.

## 4. Stack tecnológico

El detalle y la justificación de cada tecnología se documentan en **[STACK.md](STACK.md)**.

## 5. Flujo de datos de una petición

```
1. Cliente (frontend / integración externa) envía una petición HTTP.
2. middleware/  intercepta: asigna correlation-id, valida rate limit, autentica el token JWT.
3. api/         enruta la petición a la versión de contrato correspondiente y valida el
                payload contra el schema (schemas/) de entrada.
4. services/    ejecuta el caso de uso: aplica reglas de negocio y orquesta uno o más
                repository/.
5. repository/  traduce las operaciones de dominio en consultas contra database/ + models/.
6. database/    ejecuta la operación en PostgreSQL dentro de una transacción gestionada
                por services/.
7. services/    devuelve un resultado de dominio a api/.
8. api/         serializa el resultado con el schema (schemas/) de salida y responde.
9. monitoring/  registra trazas, métricas y logs estructurados de todo el recorrido,
                correlacionados por el correlation-id asignado en el paso 2.
```

En cada paso, `security/` puede intervenir (autorización a nivel de recurso) y `core/` es responsable de inyectar las dependencias concretas (sesión de base de datos, repositorios, clientes) en cada capa.

## 6. Buenas prácticas

- Las dependencias siempre fluyen hacia el centro (`api → services → repository → database`); ninguna capa interna importa una capa externa.
- Toda nueva capacidad transversal (nuevo middleware, nuevo tipo de observabilidad) se diseña primero en `core/` o la carpeta transversal correspondiente, nunca duplicada dentro de una capa de negocio.
- Los `schemas/` (contratos de API) y los `models/` (persistencia) se mantienen desacoplados de forma deliberada: un cambio en la base de datos no debe romper el contrato público de la API sin una decisión explícita.
- Toda decisión que modifique esta arquitectura se documenta como ADR (ver [adr/](adr/)) antes de implementarse.
- El código nuevo debe cumplir los estándares en [docs/standards/](../standards/) antes de fusionarse.

## 7. Roadmap

La evolución de esta arquitectura hacia una base de código ejecutable se planifica en **[docs/roadmap/ROADMAP.md](../roadmap/ROADMAP.md)**.
