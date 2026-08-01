# theme/

Configuración del tema de **Material UI**, base visual común de todas las aplicaciones TORUS construidas sobre TEAF.

## Responsabilidad

- Definir la paleta de colores, tipografía, espaciado y tokens de diseño corporativos.
- Proveer variantes de tema (por ejemplo, claro/oscuro, o personalización ligera por aplicación) manteniendo una identidad visual consistente.

## Qué NO debe contener

- Estilos específicos de un único componente (deben resolverse dentro de `components/` usando el tema, no duplicando valores aquí).

## Principio rector

Ningún componente define colores, tipografías o espaciados "a mano"; siempre consume los tokens definidos en esta carpeta, garantizando consistencia visual entre todas las aplicaciones del framework.
