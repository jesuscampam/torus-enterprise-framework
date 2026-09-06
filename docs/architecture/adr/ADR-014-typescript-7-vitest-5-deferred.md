# ADR-014 — TypeScript 7 y Vitest 5 en el frontend: no todavía

## Estado

**Rechazado por ahora** — evaluado en el cierre de Sprint 3.5c tras encontrar dos Pull Requests de
Dependabot que subían de línea major (`typescript-7.0.2`, `vitest-4.1.11`) con nombres de rama y
metadatos que afirmaban ser parches. Este ADR es el registro de por qué **no** se aceptan ahora y
qué condición reabre la decisión.

## Contexto

Al fusionar el resto de Pull Requests de Dependabot pendientes en el frontend, dos de ellos
resultaron ser saltos de versión mayor disfrazados:

| Rama | Lo que decía | Lo que hacía de verdad |
|---|---|---|
| `typescript-7.0.2` | — | TypeScript **5.9.3 → 7.0.2** |
| `vitest-4.1.11` | "4.1.10 → 4.1.11, `semver-patch`" | Vitest **4.1.10 → 5.0.0** |
| `vitest/coverage-v8-4.1.11` | mismo patrón | `@vitest/coverage-v8` **4.1.10 → 5.0.0** |

Se detectó comparando el `package.json` real de cada rama contra `main`, no confiando en el nombre
de la rama ni en el *trailer* `update-type: version-update:semver-patch` que Dependabot adjunta —
ambos eran incorrectos. Fusionar cualquiera de las tres a ciegas habría introducido una tecnología
fuera de [STACK.md](../STACK.md) sin ADR, exactamente lo que CLAUDE.md §4 prohíbe.

TypeScript ya tiene una decisión previa registrada en STACK.md:

> «TypeScript 5.9: se fija la línea 5.x y no la 7.x recién publicada (port nativo) porque el resto
> del toolchain —en particular `typescript-eslint`— aún no declara soporte. Revisable cuando lo
> haga.»

Este ADR revisa esa condición para TypeScript y añade Vitest, que no tenía decisión previa.

## Problema

¿Se sube TypeScript 5.9.3 → 7.0.2 y/o Vitest 4.1.10 → 5.0.0 en el frontend ahora, o se aplaza?

## Decisión

**Se rechazan ambas subidas en este momento**, por motivos distintos y verificables — no por
precaución genérica:

### TypeScript 7 — bloqueado por un hecho externo, no por preferencia

TypeScript 7.0 se publicó sin API programática estable; la estable llega en 7.1, prevista para
octubre de 2026. `typescript-eslint` construye sus reglas *type-aware* directamente sobre esa API,
así que no es que "aún no declare soporte" — **no puede** soportarlo hasta que la API exista. El
propio `typescript-eslint@8.67.0` que ya está fijado en `package.json` declara como rango de peer
dependency `typescript <6.1.0`; instalar TS 7 encima rompe la instalación, no solo el lint.

No hay una alternativa intermedia razonable para este framework: el patrón que están usando algunos
equipos (instalar TypeScript 6 con un alias de paquete para las herramientas dependientes de la API
y TypeScript 7 aparte solo para `tsc`) añade una capa de indirección al *toolchain* de un frontend
que hoy tiene cuatro piezas decididas en ADR-013 y ninguna redundante — desproporcionado para ganar
una versión de compilador que no aporta nada usable todavía (el port nativo es una reescritura de
rendimiento, sin comportamiento nuevo relevante aquí).

**Condición de reapertura**: `typescript-eslint` publica una versión con `peerDependencies` que
acepte TypeScript 7.x. Verificable en su changelog sin necesitar acceso a un entorno con TS 7
instalado.

### Vitest 5 — no bloqueado, pero no auditado lo suficiente para aceptarlo sin más

A diferencia de TypeScript 7, aquí no hay un bloqueo externo. Se auditó el código actual contra las
roturas de compatibilidad documentadas por el propio proyecto:

| Cambio de Vitest 5 | Resultado de la auditoría en este repo |
|---|---|
| `clearMocks` pasa a `true` por defecto | Sin efecto: cada fichero de test que depende de conteos de llamadas ya limpia sus dobles a mano (`vi.restoreAllMocks()` en `client.test.ts`, `LoginPage.test.tsx`, `routes.test.tsx`, `ModulesPage.test.tsx`, `RuntimePage.test.tsx`, `EventsPage.test.tsx`, `DashboardPage.test.tsx`; `vi.clearAllMocks()` en `authStore.test.ts`), o construye el doble de nuevo en cada `beforeEach` (`client.test.ts`). |
| `vi.mock`/`vi.unmock`/`vi.hoisted` fuera del nivel superior del módulo pasa de aviso a error | Sin efecto: el único uso (`authStore.test.ts`) ya está al nivel superior del módulo. |
| `test.sequential`/`describe.sequential` eliminados | Sin efecto: no se usan en el repo. |
| Vitest 5 exige **Vite ≥ 6.4.0** | Ya cumplido: Vite está en 8.2.2 tras el barrido de Dependabot de este mismo cierre. |
| Vitest 5 exige **Node ≥ 22.12.0** | **No cumplido por declaración**: `frontend/package.json` fija `"engines": {"node": ">=20.19.0"}`. Subir Vitest obligaría a subir también el suelo de Node del frontend — una decisión de infraestructura que afecta a cualquier máquina de desarrollo o imagen de CI fijada en Node 20/21, no solo a una dependencia de test. |

Cuatro de cinco puntos están limpios. El quinto —el suelo de Node— es del mismo calibre que decidir
`requires-python` en el backend: no se cambia de pasada dentro de un ADR sobre herramientas de test.
Aceptar Vitest 5 aquí implicaría subir el suelo de Node sin haberlo evaluado como su propia decisión
(qué imágenes de CI, qué máquinas de desarrollo, qué otra pieza del frontend podría depender del
Node instalado).

**Condición de reapertura**: se decide subir el suelo de Node del frontend a ≥ 22.12 como su propia
decisión (documentada aquí mismo, ampliando este ADR, o en uno nuevo si arrastra más consecuencias
de las previstas) — momento en el que la subida de Vitest se vuelve una formalidad ya auditada.

### Alternativa descartada: aceptar solo Vitest 5 sin subir Node

Se consideró instalarlo igualmente confiando en que Node 22.22.2 (la versión real de este entorno)
lo soporta. Se descarta: el campo `engines` es una promesa a quien clone el repositorio, no una
descripción de esta máquina. Instalar una dependencia que ya no cumple lo que `engines` promete deja
el manifiesto mintiendo, y es exactamente la clase de deriva silenciosa que este mismo cierre de
sprint encontró y corrigió en el módulo de secretos del backend (pruebas que nunca corrían).

## Consecuencias

### Positivas

- El frontend no queda con una combinación TypeScript/`typescript-eslint` rota, ni con un suelo de
  Node que no coincide con lo declarado en `engines`.
- Quedan documentadas condiciones de reapertura verificables y objetivas para ambas piezas, en vez
  de "revisar más adelante" sin criterio.
- La auditoría de Vitest 5 queda escrita: cuando se decida subir Node, la mayor parte del trabajo de
  verificación de este ADR sigue siendo válida y no hay que rehacerla.

### Negativas / Trade-offs

- El frontend se queda sin las correcciones y mejoras propias de Vitest 5 (mejor manejo de
  aserciones asíncronas olvidadas, entre otras) hasta que se resuelva el suelo de Node.
- Dos Pull Requests de Dependabot (`typescript-7.0.2`, `vitest-4.1.11` y su pareja de cobertura)
  quedan abiertos indefinidamente hasta que se cumplan las condiciones de arriba; hay que recordarlo
  o Dependabot los seguirá reabriendo/actualizando sin que nadie los revise a fondo.
- Confiar en el nombre de rama o en el *trailer* de Dependabot para clasificar un cambio como
  "seguro" quedó demostrado como insuficiente en este mismo cierre — cualquier automatización futura
  de fusión de dependencias del frontend debe comparar el `package.json` real, no el metadato.

---

## Checklist antes de marcar como "Aceptado"

- [x] Se evaluaron y descartaron explícitamente al menos una alternativa (instalar Vitest 5 sin
      subir el suelo de Node).
- [x] El índice `docs/architecture/adr/README.md` está actualizado con la nueva fila.
- [ ] No aplica — no reemplaza ningún ADR anterior (revisa la condición de TypeScript ya anotada en
      STACK.md, sin contradecirla).
- [x] No introduce tecnología nueva — al contrario, deja fijadas las versiones ya aprobadas en
      ADR-013; no hay cambio pendiente en STACK.md más allá de lo que ya dice.
