# anonymous-endpoint/

Marcar explícitamente un endpoint como público con `@allow_anonymous()`, en contraste con uno protegido por `@authorize()`.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- `GET /status` (con `@allow_anonymous()`) responde `200` sin ninguna credencial.
- `GET /account` (con `@authorize()`) responde `401` sin credenciales — el contraste es el punto del ejemplo.
- `@allow_anonymous()` es un *no-op* en tiempo de ejecución: `SecurityMiddleware` nunca bloquea una petición por falta de autenticación, así que un endpoint sin `@authorize()` ya sería público de todas formas. El decorador existe para dejar esa intención explícita en el código, no para cambiar el comportamiento.
