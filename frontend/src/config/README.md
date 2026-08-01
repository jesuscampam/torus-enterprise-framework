# config/

Configuración del frontend por entorno, en cumplimiento del principio **Configuration by Environment**.

## Responsabilidad

- Centralizar valores que varían por entorno (URL base de la API, feature flags, claves públicas) leídos de variables de entorno de build (`import.meta.env` / equivalente).
- Exponer una única fuente de configuración tipada consumida por `services/` y el resto de la aplicación.

## Qué NO debe contener

- Secretos: el frontend nunca maneja credenciales o claves privadas; solo configuración pública no sensible.
