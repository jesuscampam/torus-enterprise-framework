# cors-policy/

La política CORS de `teaf.api` (Sprint 2.9, [ADR-009](../../docs/architecture/adr/ADR-009-enterprise-api-protection.md)): orígenes con comodín de subdominio, credenciales, cabeceras expuestas y comprobación previa.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- `https://*.torus.com` acepta `app.torus.com` y `portal.torus.com`, pero **no** `torus.com` (no es un subdominio) ni `evil-torus.com` (no es el mismo dominio). Ese es el motivo de no usar `CORSMiddleware` de Starlette, que no ofrece comodines de subdominio — ver [CORS.md](../../docs/api/CORS.md).
- Con `allow_credentials=True` la respuesta lleva **el origen concreto**, nunca `*`. Un navegador rechaza esa combinación, y "arreglarla" devolviendo el comodín convertiría cualquier web en cliente autenticado de la API.
- `Vary: Origin` va siempre: sin él, una caché intermedia podría servir la respuesta de un origen permitido a otro que no lo está.
- Un preflight de un origen no permitido responde `403` **sin** cabeceras CORS: es exactamente lo que el navegador interpreta como "origen no autorizado".
- Las cabeceras CORS acompañan también al `429`. Por eso CORS es el middleware más externo de la cadena: un error sin ellas se le presenta al desarrollador como un "failed to fetch" genérico en lugar del motivo real.
