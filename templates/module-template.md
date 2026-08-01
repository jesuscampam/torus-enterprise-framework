# Plantilla — Nuevo módulo del framework

> PLANTILLA — no ejecutable, no forma parte de la aplicación. Cópiala como checklist al dar de alta un módulo nuevo (ver [CLAUDE.md](../CLAUDE.md), sección 14).

## Cómo usar esta plantilla

1. Reemplaza `{{NombreModulo}}` por el nombre real del módulo (por ejemplo, `Notifications`).
2. Completa cada sección antes de crear una sola carpeta.
3. Añade el módulo a [`docs/architecture/MODULE-CATALOG.md`](../docs/architecture/MODULE-CATALOG.md) con su fila correspondiente.
4. Solo entonces crea la estructura de carpetas descrita más abajo, cada una con su propio `README.md`.

---

## Ficha del módulo `{{NombreModulo}}`

- **Objetivo**: <qué problema resuelve este módulo dentro del framework>
- **Capas que involucra**: <por ejemplo: services/, repository/, models/, schemas/>
- **Dependencias de otros módulos**: <por ejemplo: depende de security/ para autorización>
- **Versión objetivo (roadmap)**: <V1 / V2 / V3 / V4 / V5>
- **Nivel de reutilización esperado**: <Alto / Medio / Bajo — ¿lo usarán todas las aplicaciones o solo algunas?>
- **¿Requiere ADR?**: <Sí, si introduce un patrón o tecnología nueva / No, si extiende un patrón ya aprobado>

## Estructura de carpetas prevista

```
backend/
└── {{nombre_modulo}}/
    └── README.md   # responsabilidad del módulo, siguiendo el estilo de backend/*/README.md existentes
```

Si el módulo requiere presencia en varias capas transversales existentes (por ejemplo, un endpoint en `api/`, un caso de uso en `services/`, un repositorio en `repository/`), documenta en el `README.md` del módulo cómo se distribuye entre ellas — no se crea una carpeta de primer nivel nueva para cada capa que ya existe.

## Checklist de alta

- [ ] Ficha completada y añadida a `MODULE-CATALOG.md`.
- [ ] ¿Requiere ADR? Si sí, redactado y aceptado antes de continuar (ver `adr-template.md`).
- [ ] Estructura de carpetas creada, con `README.md` de responsabilidad en cada una.
- [ ] Entrada correspondiente añadida a `docs/roadmap/BACKLOG.md` si el módulo forma parte de una épica/feature planificada.
- [ ] Estándares aplicables identificados (ver tabla de `CLAUDE.md`, sección 7).
