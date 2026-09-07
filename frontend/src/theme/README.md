# theme/

Configuración del tema de **Material UI**, base visual común de todas las aplicaciones TORUS construidas sobre TEAF.

## Responsabilidad

- Definir la paleta de colores, tipografía, espaciado y tokens de diseño corporativos.
- Proveer variantes de tema (por ejemplo, claro/oscuro, o personalización ligera por aplicación) manteniendo una identidad visual consistente.

## Paleta corporativa TORUS

`index.ts` implementa la paleta oficial de marca (extraída y verificada por contraste WCAG a partir de `Plantilla de colores.pptx`, raíz del repositorio): `primary` (rojo TORUS), `secondary` (verde de marca, con una variante oscurecida como `main` porque el tono original no alcanza 4.5:1 usado como texto), `text.primary` (carbón) y `torus.gray` — un token de superficie propio (fondos de navegación y cabeceras de tabla), añadido vía extensión de tipos de MUI en vez de forzarlo dentro de `grey` (que MUI reutiliza internamente para estados deshabilitados).

`error`/`success`/`warning`/`info` se mantienen en los valores por defecto de MUI a propósito: son colores de estado, no de identidad de marca. Modo oscuro y variantes por producto quedan fuera de alcance hasta que una aplicación futura los necesite.

## Qué NO debe contener

- Estilos específicos de un único componente (deben resolverse dentro de `components/` usando el tema, no duplicando valores aquí).

## Principio rector

Ningún componente define colores, tipografías o espaciados "a mano"; siempre consume los tokens definidos en esta carpeta, garantizando consistencia visual entre todas las aplicaciones del framework.
