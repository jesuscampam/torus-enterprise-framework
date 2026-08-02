# Árbol de decisiones — TEAF

Ayuda a cualquier desarrollador (humano o agente de IA) a decidir rápidamente qué módulo usar, cuándo crear uno nuevo y cuándo se necesita un ADR, sin tener que releer toda la documentación cada vez. Complementa [FRAMEWORK-BLUEPRINT.md](FRAMEWORK-BLUEPRINT.md) y [MODULE-CATALOG.md](MODULE-CATALOG.md) — este documento no redefine ninguna regla, solo las convierte en un flujo de decisión navegable.

## 1. ¿Qué módulo utilizar?

```mermaid
flowchart TD
    Q["¿Qué necesito hacer?"]
    Q --> A["Persistir/consultar datos"]
    Q --> B["Ejecutar algo en segundo plano o programado"]
    Q --> C["Generar/procesar texto con un LLM, embeddings o RAG"]
    Q --> D["Exponer herramientas/contexto a un agente de IA"]
    Q --> E["Autenticar/autorizar a un usuario"]
    Q --> F["Enviar/recibir eventos de un sistema externo"]
    Q --> G["Notificar a un usuario (email, push, chat)"]
    Q --> H["Guardar o servir un archivo/blob"]
    Q --> I["Registrar una acción sensible con fines de cumplimiento"]

    A --> Database["Usa Database\n(repository/ + database/)"]
    B --> Scheduler["Usa Scheduler"]
    C --> AI["Usa AI"]
    D --> MCP["Usa MCP\n(requiere AI)"]
    E --> Security["Usa Security"]
    F --> Webhooks["Usa Webhooks\n(o un Connector si ya existe uno para ese sistema)"]
    G --> Notifications["Usa Notifications\n(planeado, V4)"]
    H --> Storage["Usa Storage\n(planeado, V4)"]
    I --> Audit["Usa Audit\n(planeado, V2)"]
```

Ver la ficha completa de cada módulo (objetivo, estado, dependencias) en [MODULE-CATALOG.md](MODULE-CATALOG.md).

## 2. ¿Cuándo usar Database?

```mermaid
flowchart TD
    Q["¿El dato debe sobrevivir al proceso\ny ser consultable después?"]
    Q -->|"Sí"| Y["Usa Database vía repository/\n(nunca SQL directo fuera de repository/)"]
    Q -->|"No, es efímero/derivado en memoria"| N["No uses Database.\n¿Es una cola/estado de job? -> ver Scheduler"]
```

Regla asociada: `repository/` nunca contiene lógica de negocio (ver [DATABASE-STANDARD.md](../standards/DATABASE-STANDARD.md)).

## 3. ¿Cuándo usar Scheduler?

```mermaid
flowchart TD
    Q["¿La acción debe ejecutarse en un\nmomento futuro o de forma recurrente,\nsin que un usuario espere la respuesta?"]
    Q -->|"Sí"| Y["Usa Scheduler\n(coordinado multi-instancia, ver ADR-005)"]
    Q -->|"No, es síncrono dentro de una petición HTTP"| N["No uses Scheduler.\nEjecútalo directamente en el Service del caso de uso"]
```

## 4. ¿Cuándo usar AI?

```mermaid
flowchart TD
    Q["¿La funcionalidad requiere generación de texto,\nembeddings, o razonamiento de un LLM?"]
    Q -->|"Sí"| Y["Usa AI (interfaz de ai/), nunca el SDK\nde un proveedor directamente"]
    Y --> Y2["¿Necesito exponer esto como herramienta\npara que un agente externo lo invoque?"]
    Y2 -->|"Sí"| MCP2["Usa también MCP\n(MCP depende de AI, nunca al revés)"]
    Y2 -->|"No"| DONE["Suficiente con AI"]
    Q -->|"No"| N["No uses AI"]
```

Regla asociada: `AI` nunca accede a `Database` directamente — la persistencia de embeddings pasa por `repository/` (ver [FRAMEWORK-BLUEPRINT.md, sección 6](FRAMEWORK-BLUEPRINT.md#6-reglas-de-dependencias) y [`ai-provider-architecture.mmd`](../diagrams/ai-provider-architecture.mmd)).

## 5. ¿Cuándo usar MCP?

```mermaid
flowchart TD
    Q["¿Necesito que un agente de IA (interno o externo)\ndescubra e invoque capacidades de TEAF de forma\nestandarizada (tools, resources, prompts)?"]
    Q -->|"Sí"| Y["Usa MCP\n(ver mcp-architecture.mmd)"]
    Q -->|"No, solo necesito llamar a un LLM yo mismo"| N["Usa AI directamente, no necesitas MCP"]
```

## 6. ¿Cuándo crear un nuevo módulo?

```mermaid
flowchart TD
    Q1["¿La responsabilidad ya la cubre\nun módulo existente de MODULE-CATALOG.md?"]
    Q1 -->|"Sí"| N1["No crees un módulo nuevo.\nExtiende el existente (ver EXTENSIBILITY.md)"]
    Q1 -->|"No"| Q2["¿La usarán varias aplicaciones futuras\n(no solo una)?"]
    Q2 -->|"No, es específico de una aplicación"| N2["No pertenece a TEAF.\nImplementa en la aplicación, no en el framework"]
    Q2 -->|"Sí"| Q3["¿Puedo expresarla sin introducir\nuna dependencia nueva hacia un módulo\nde nivel igual o superior?"]
    Q3 -->|"No, requeriría una dependencia circular"| N3["Redisénala: extrae la parte compartida\na un módulo de nivel inferior (Core/Shared)"]
    Q3 -->|"Sí"| Y["Crea el módulo:\n1. Ficha en module-template.md\n2. Alta en MODULE-CATALOG.md\n3. Actualiza dependency-map.mmd / module-map.mmd"]
```

## 7. ¿Cuándo crear un nuevo ADR?

```mermaid
flowchart TD
    Q1["¿Introduce una tecnología fuera de STACK.md?"]
    Q1 -->|"Sí"| Y["Requiere ADR"]
    Q1 -->|"No"| Q2["¿Cambia una capa, patrón o regla\nya aceptada en el Blueprint\n(sección 6 u 11)?"]
    Q2 -->|"Sí"| Y
    Q2 -->|"No"| Q3["¿Impacta a todas las aplicaciones\nfuturas construidas sobre TEAF?"]
    Q3 -->|"Sí"| Y
    Q3 -->|"No, es un cambio pequeño dentro\nde un patrón ya existente"| N["No requiere ADR.\nImplementa siguiendo el estándar aplicable"]
```

Ver el flujo completo de propuesta y aceptación en [CLAUDE.md, sección 12](../../CLAUDE.md) y la plantilla en [`/templates/adr-template.md`](../../templates/adr-template.md).
