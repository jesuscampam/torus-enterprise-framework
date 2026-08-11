# e2e/

Pruebas end-to-end: verifican un flujo de negocio completo a través de la API real (y, cuando aplique, del frontend), simulando el comportamiento de un consumidor externo real.

## Convenciones

- Se ejecutan contra un entorno desplegado (local completo vía Docker Compose, o un entorno de staging), nunca contra dependencias dobladas.
- Se reservan para los flujos más críticos del framework y, en el futuro, de las aplicaciones construidas sobre él — no se busca exhaustividad aquí, sino confianza en los caminos de mayor impacto.

## Contenido actual

| Archivo | Qué valida |
|---|---|
| `test_frontend_api_contract.py` | Que el TEAF real emite exactamente la forma que el frontend MVP espera. |

### `test_frontend_api_contract.py` — la costura entre las dos mitades

El frontend mantiene sus tipos a mano en `frontend/src/types/runtime.ts`: todavía
no se generan desde el OpenAPI del backend (entrada abierta en
[BACKLOG.md](../../docs/roadmap/BACKLOG.md)). Un fichero de tipos escrito a mano
se desincroniza **en silencio**: el backend renombra un campo, TypeScript sigue
compilando porque no sabe nada del servidor, y el fallo solo aparece en el
navegador.

Estas pruebas cierran ese hueco. Declaran la forma que el frontend lee y la
comprueban contra la respuesta real de una `Application`, así que un cambio de
contrato rompe la suite del backend en vez de romper la pantalla de un usuario.

Verifican además una propiedad arquitectónica: la aplicación se construye con
`from teaf import Application` —la superficie pública, la misma que usaría
cualquier consumidor externo—, de modo que el frontend queda demostrado como
consumidor de la API pública y no de `teaf._internal`.

**Lo que no comprueban** es el contenido: cuántos módulos hay o cómo se llaman
depende de qué registre cada aplicación y no forma parte del contrato.

## El recorrido de usuario vive en el frontend

El flujo completo —entrar, recorrer las cuatro pantallas, cerrar sesión— está en
`frontend/src/e2e.test.tsx`, no aquí. Es deliberado: ejercita pantallas, rutas,
store y cliente HTTP, que son piezas de TypeScript, y ejecutarlo con Vitest evita
levantar un navegador y un servidor para cada verificación.

Ese recorrido usa un doble del backend a la altura de `fetch`, con cargas útiles
que **estas pruebas garantizan que son las reales**. Las dos piezas se sostienen
mutuamente: aquí se fija el contrato, allí se recorre la aplicación que lo
consume.

### Lo que ninguna de las dos cubre todavía

Un E2E de navegador contra la pila desplegada (Playwright o equivalente). Queda
fuera por una razón concreta y no por presupuesto: **TEAF no expone endpoints de
login** —entrega primitivas de seguridad y cada aplicación publica sus rutas
([ADR-013](../../docs/architecture/adr/ADR-013-enterprise-frontend-stack.md))—,
así que la mitad de autenticación de ese recorrido habría que simularla igual.
El momento natural para montarlo es cuando la Reference App, que sí publica sus
rutas de sesión, se valide como consumidor externo real.
