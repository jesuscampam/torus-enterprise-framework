import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material';
import { useState, type FormEvent, type ReactElement } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '@/hooks/useAuth';

interface LocationState {
  from?: string;
}

/**
 * Pantalla de inicio de sesión.
 *
 * Referencia de cómo se consume el flujo de autenticación del framework. Una
 * aplicación concreta la sustituirá por la suya (branding, SSO, recuperación de
 * contraseña) sin tocar `store/` ni `services/`.
 */
export function LoginPage(): ReactElement {
  const { login, error, isAuthenticating, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const from = (location.state as LocationState | null)?.from ?? '/';

  if (isAuthenticated) return <Navigate to={from} replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    try {
      await login({ username, password });
      void navigate(from, { replace: true });
    } catch {
      // El mensaje ya está en `error`; el store lo dejó listo para mostrar.
    }
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', pt: 6 }}>
      <Paper sx={{ p: 4, width: '100%', maxWidth: 400 }} elevation={2}>
        <Typography variant="h5" component="h2" gutterBottom>
          Iniciar sesión
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={(event) => void handleSubmit(event)}>
          <TextField
            label="Usuario"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            fullWidth
            required
            margin="normal"
            autoComplete="username"
          />
          <TextField
            label="Contraseña"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            fullWidth
            required
            margin="normal"
            autoComplete="current-password"
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
            sx={{ mt: 3 }}
            disabled={isAuthenticating}
          >
            {isAuthenticating ? 'Entrando…' : 'Entrar'}
          </Button>
        </form>
      </Paper>
    </Box>
  );
}
