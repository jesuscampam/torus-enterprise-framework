# ai/

Abstracciones **AI-Ready** del framework: la capa que permite integrar Inteligencia Artificial en cualquier aplicación construida sobre TEAF sin acoplarla a un proveedor concreto.

## Responsabilidad

- Definir interfaces de cliente LLM (generación de texto, chat, function/tool calling) independientes del proveedor subyacente.
- Definir interfaces de generación y almacenamiento de embeddings, con integración prevista hacia `pgvector` sobre PostgreSQL (ver [ADR-002](../../docs/architecture/adr/ADR-002-uso-de-postgresql.md)).
- Gestión y versionado de prompts como artefactos propios del framework, no como strings embebidos en `services/`.
- Proveer abstracciones de vector store consumibles por `services/` a través de interfaces, siguiendo el mismo espíritu que el Repository Pattern.

## Qué NO debe contener

- Lógica de negocio específica de una aplicación (por ejemplo, el prompt concreto de un asistente de un producto determinado).
- Acoplamiento directo a un proveedor de IA en las capas superiores (`api/`, `services/` consumen la interfaz, no el SDK del proveedor).

## Estado actual

Solo estructura; la implementación concreta llega en la Versión 4 del [roadmap](../../docs/roadmap/ROADMAP.md).
