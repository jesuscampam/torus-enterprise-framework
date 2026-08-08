# Preparación para producción — v0.10.0-alpha

> **Actualizado en Sprint 3.0.** Los cuatro pendientes que condicionaban esta evaluación **se han
> cerrado**. El estado vigente:
>
> | Punto | v0.9.1-alpha | v0.9.2-alpha | v0.10.0-alpha |
> |---|---|---|---|
> | Cabeceras de seguridad HTTP | ❌ Declaradas, no implementadas | ✅ Implementadas + 31 pruebas | ✅ Sin cambios |
> | Auditoría de vulnerabilidades | ❌ Nunca ejecutada | ✅ Puerta de calidad; 7 avisos aceptados | ✅ **0 avisos, 0 excepciones aceptadas** |
> | `trust_forwarded_headers` | ⚠️ Riesgo silencioso | ⚠️ Riesgo documentado, con aviso al arrancar | ✅ **Cerrado** con `api_trusted_proxies` ([ADR-011](architecture/adr/ADR-011-trusted-proxy-architecture.md)) |
> | Escalado horizontal | ❌ Almacenes por proceso | ❌ Igual | ✅ **Desbloqueado** — almacenes distribuidos sobre Redis ([ADR-012](architecture/adr/ADR-012-redis-optional-infrastructure.md)) |
> | Longitud del secreto JWT | ❌ Sin política | ❌ Igual | ✅ Mínimo por algoritmo, validado al arrancar |
> | Puertas de calidad | 10/10 | 11/11 | **12/12** (nueva: `build`) |
> | Pruebas | 1.126 · 98% | 1.170 · 98% | **1.263 · 98%** |
>
> **Qué falta ya no es deuda de la línea 2.9**, sino alcance de sprints siguientes: observabilidad
> completa (3.1), gestión empresarial de secretos (3.2), EventBus distribuido (3.3) y resiliencia
> avanzada (3.4). Dos limitaciones conocidas quedan documentadas y en el backlog: la cuota
> distribuida no es atómica, y sin configurar `api_trusted_proxies` el comportamiento de las
> cabeceras de reenvío sigue siendo el de v0.9.2-alpha.

---

# Preparación para producción — v0.9.1-alpha (revisión original)

Estado real de TEAF frente a un despliegue en producción: qué está listo, qué falta y qué hay que
resolver **fuera** del framework. Es el documento que se lee antes de decidir si se declara
v1.0-beta.

Resultado de Sprint 2.9.1, cuyo objetivo era exactamente este: no añadir funcionalidad, sino
convertir lo que ya existía en algo desplegable.

## Veredicto

**TEAF está técnicamente listo para v1.0-beta, con una condición.** La calidad, la compatibilidad
y el rendimiento están verificados de forma mecánica y en verde. Pero la revisión de seguridad
dejó un hallazgo de severidad alta sin corregir —las cabeceras de seguridad HTTP están declaradas
y no implementadas ([SECURITY-REVIEW.md](SECURITY-REVIEW.md) H-1)—, y **no se corrigió a propósito**:
este Sprint tenía prohibido añadir funcionalidad.

Esa decisión es del usuario, no del framework. Las dos salidas legítimas:

1. Un Sprint que implemente las cabeceras antes de declarar v1.0-beta, o
2. Declarar v1.0-beta documentando explícitamente que las cabeceras son responsabilidad del proxy
   inverso — y corregir [SECURITY-STANDARD.md §7](standards/SECURITY-STANDARD.md), que hoy promete
   lo que el framework no hace.

Lo que no es aceptable es dejarlo como está: un `security_headers_enabled: bool = True` que no
activa nada comunica una protección inexistente.

## Estado por área

| Área | Estado | Evidencia |
|---|---|---|
| Puertas de calidad | ✅ | 10/10 en verde, un solo comando |
| Pruebas | ✅ | 1.126 pruebas, **98%** de cobertura (objetivo 95%) |
| Tipado | ✅ | `mypy --strict`, **0 errores** en 225 ficheros |
| Arquitectura | ✅ | **0 ciclos** de dependencias en 225 módulos |
| API pública | ✅ | 192 símbolos, **100%** compatible con v0.9.0-alpha |
| Rendimiento | ✅ | Arranque **5,5× más rápido**; baseline fijada |
| Estabilidad bajo carga | ✅ | **0 errores** en 9 escenarios × 2.000 peticiones |
| Memoria | ✅ | Fuga acotada y verificada (−99,3% de retención) |
| Ejemplos | ✅ | **25/25** ejecutan correctamente |
| Aplicación de referencia | ⚠️ | 39/40 — un fallo preexistente, ajeno a este Sprint |
| Seguridad | ⚠️ | 1 hallazgo alto, 1 medio, 2 bajos — ninguno corregido, por diseño |
| Auditoría de dependencias | ⚠️ | Sin contrastar contra base de datos de vulnerabilidades |

## Lo que está verificado

### Un solo comando

```bash
python scripts/quality_gates.py
```

Diez puertas: formato, lint, tipos, ciclos de importación, espacio de nombres interno, frontera de
la API pública, compatibilidad de firmas, **arranque real de la aplicación**, pruebas con
cobertura y benchmarks sin regresión. Detalle en
[QUALITY-GATES.md](standards/QUALITY-GATES.md).

La puerta `startup` merece mención aparte: es la única que **ejecuta** el framework de extremo a
extremo —construye una `Application`, corre el ciclo de vida ASGI completo, llama a los siete
endpoints de sistema y la apaga—. Ninguna de las otras nueve detecta un fallo de cableado, y ese
es exactamente el fallo que aparece en producción.

### Estabilidad bajo concurrencia

Nueve escenarios × 2.000 peticiones con 32 en vuelo: **cero errores**. Ninguna ruta degenera en
500 bajo carga. Cifras en [PERFORMANCE.md](PERFORMANCE.md).

### Memoria acotada

La fuga de los almacenes en memoria —crecimiento sin techo proporcional a la **cardinalidad** del
tráfico, que es lo que un atacante controla— está corregida y verificada empíricamente: 1.536 → 10
entradas retenidas. Era el hallazgo de corrección más grave del Sprint.

## Lo que falta

### 1. Cabeceras de seguridad HTTP (alta)

Ver [SECURITY-REVIEW.md](SECURITY-REVIEW.md) H-1. Requiere un Sprint propio: es funcionalidad
nueva.

### 2. Auditoría de vulnerabilidades de dependencias

No hay `pip-audit` ni `safety` en el entorno, así que el árbol de 20 dependencias **no se ha
contrastado contra ninguna base de datos de vulnerabilidades**. Las versiones están fijadas y son
recientes, pero eso es conocimiento, no verificación. Es la mayor laguna de la revisión.

**Recomendación**: añadir `pip-audit` a `requirements-dev.txt` y una puerta que lo ejecute. Es
barato y cierra un hueco real.

### 3. El fallo de la aplicación de referencia

`teaf-reference-app` pasa 39 de 40 pruebas. La que falla,
`test_task_module_appears_in_runtime_info`, espera `registeredModules >= 8` («7 built-ins + task»)
y obtiene 6, porque los Sprints 2.7 y 2.8 retiraron los descriptores placeholder `security` y
`telemetry` de `_INFRASTRUCTURE_MODULES` al implementarlos de verdad.

**No lo causó este Sprint**: se verificó volviendo al commit de v0.9.0-alpha y el fallo es
idéntico (`assert 6 >= 8`). No se corrigió en ninguno de los dos lados —el usuario pidió
explícitamente no modificar la aplicación de referencia, y ajustar el framework para satisfacer
una prueba sería exactamente al revés—. Corresponde a un Sprint de la aplicación de referencia.

### 4. Almacenamiento distribuido

Los almacenes de rate limiting, cuotas e idempotencia son **en memoria**: cada proceso tiene los
suyos. Con varias réplicas, un límite de 100 req/min con 4 réplicas es en la práctica 400.

El contrato de Redis existe y está preparado
([ADR-009](architecture/adr/ADR-009-enterprise-api-protection.md)), pero
`teaf/_internal/api/providers/redis.py` lanza `NotImplementedError`. **Antes de escalar
horizontalmente con límites que importen, hay que implementarlo.**

## Lo que corresponde al despliegue, no al framework

Ningún framework resuelve esto por sí solo; se lista para que no se dé por hecho:

| Responsabilidad | Nota |
|---|---|
| Terminación TLS | El framework nunca sirve TLS directamente. |
| Cabeceras de seguridad HTTP | Mitigación de H-1 mientras no exista el middleware. |
| Reescritura de `X-Forwarded-For` | Un proxy debe **reescribirla**, no propagar la del cliente ([SECURITY-REVIEW.md](SECURITY-REVIEW.md) H-2). |
| Secretos (`JWT_SECRET`, `API_KEY_HASH_SECRET`, ...) | Desde un gestor de secretos, nunca desde el repositorio. |
| Escala horizontal | Por procesos: un bucle de eventos satura un núcleo. |
| Retención de logs y trazas | TEAF los emite; recogerlos y retenerlos es del agente. |
| Migraciones de base de datos | Alembic está integrado; ejecutarlas es del despliegue. |

## Antes de declarar v1.0-beta

- [ ] Decidir sobre H-1: implementar las cabeceras, o documentar que son del proxy y corregir
      SECURITY-STANDARD.md §7.
- [ ] Añadir `pip-audit` y ejecutarlo.
- [ ] Decidir el valor por defecto de `trust_forwarded_headers` (H-2).
- [ ] Implementar los proveedores Redis si se va a escalar horizontalmente.
- [ ] Corregir la prueba de la aplicación de referencia (en su repositorio).
- [ ] Corregir el comentario obsoleto sobre secretos (H-3, trivial).

Los tres primeros condicionan la seguridad de un despliegue real. Los tres últimos son deuda
conocida y acotada.
