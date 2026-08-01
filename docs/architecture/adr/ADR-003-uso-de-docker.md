# ADR-003: Uso de Docker

## Estado

Aceptado

## Contexto

TEAF debe funcionar de forma idéntica en el entorno local de desarrollo, en el hosting de POC (Render) y en producción (Azure App Service). Sin un mecanismo de empaquetado estándar, cada aplicación construida sobre el framework corre el riesgo de divergir en dependencias del sistema operativo, versiones de Python/Node o configuración de red, generando el clásico problema de "funciona en mi máquina".

## Problema

¿Qué mecanismo de empaquetado y ejecución debe adoptar TEAF como estándar para garantizar paridad entre entornos y cumplir el principio Docker First?

## Decisión

Se adopta **Docker** como mecanismo oficial de contenerización de todos los componentes de TEAF (backend, frontend, y servicios auxiliares).

Motivos determinantes:

- Estándar de facto de la industria, con soporte nativo tanto en Render (POC) como en Azure App Service (producción vía contenedores Linux).
- Garantiza paridad exacta de entorno de ejecución entre desarrollo local, integración continua (GitHub Actions) y producción.
- Aísla las dependencias de cada componente (versión de Python, de Node, librerías del sistema) sin contaminar la máquina host ni otros componentes.
- Facilita la orquestación local de servicios dependientes (backend + PostgreSQL) mediante composición de contenedores.
- Compatible con la estrategia AI Ready: modelos, librerías de inferencia o vector stores adicionales pueden empaquetarse de forma aislada sin afectar al resto del stack.

## Consecuencias

### Positivas

- Onboarding de nuevos desarrolladores reducido a "clonar y levantar contenedores", sin instalación manual de dependencias de sistema.
- Los mismos artefactos (imágenes) que se prueban en CI son los que se despliegan en producción, eliminando divergencias de última hora.
- Escalado horizontal en Azure App Service simplificado al tratarse de contenedores sin estado.

### Negativas / Trade-offs

- Introduce una capa de aprendizaje adicional para desarrolladores sin experiencia previa en Docker.
- Requiere mantener Dockerfiles optimizados (multi-stage builds, imágenes base mínimas) para evitar tiempos de build e imágenes innecesariamente grandes; esta responsabilidad se define formalmente en la carpeta `docker/` a partir de la Versión 1 del roadmap.
- Añade un componente más a versionar y mantener actualizado por motivos de seguridad (parches de la imagen base).
