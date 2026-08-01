# e2e/

Pruebas end-to-end: verifican un flujo de negocio completo a través de la API real (y, cuando aplique, del frontend), simulando el comportamiento de un consumidor externo real.

## Convenciones

- Se ejecutan contra un entorno desplegado (local completo vía Docker Compose, o un entorno de staging), nunca contra dependencias dobladas.
- Se reservan para los flujos más críticos del framework y, en el futuro, de las aplicaciones construidas sobre él — no se busca exhaustividad aquí, sino confianza en los caminos de mayor impacto.
