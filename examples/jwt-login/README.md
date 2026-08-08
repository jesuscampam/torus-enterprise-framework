# jwt-login/

Login con usuario/contraseña que emite un JWT (`JWTProvider`), y un endpoint protegido con `@authorize()` que exige ese token.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- `Argon2PasswordHasher` verifica la contraseña contra un hash — nunca se compara texto plano.
- `POST /login` emite un `TokenPair` (`accessToken`/`refreshToken`) solo si la contraseña es correcta.
- `GET /me` está protegido con `@authorize()` sin argumentos — exige *alguna* autenticación válida, sin exigir un rol/permiso concreto.
- `SecurityMiddleware` resuelve la identidad de cada petición antes de que llegue al handler; `current_principal` (vía `Depends`) es cómo el handler la lee.
