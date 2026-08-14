import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { useAuthStore } from '@/store/authStore';
import type { Principal } from '@/types/auth';

import { ProtectedRoute } from './ProtectedRoute';

const principal: Principal = {
  identity: {
    id: 'u-1',
    providerId: 'jwt',
    claims: { subject: 'u-1', name: 'Ada' },
    authenticated: true,
  },
  roles: ['operator'],
  permissions: ['incidents:read'],
};

/** Monta la ruta protegida junto a los destinos de redirección posibles. */
function renderProtected(element: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={['/privado']}>
      <Routes>
        <Route path="/privado" element={element} />
        <Route path="/login" element={<p>Pantalla de login</p>} />
        <Route path="/forbidden" element={<p>Acceso denegado</p>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthStore.setState({
      status: 'anonymous',
      principal: null,
      tokens: null,
      error: null,
    });
  });

  it('redirige al login cuando no hay sesión', () => {
    renderProtected(
      <ProtectedRoute>
        <p>Contenido privado</p>
      </ProtectedRoute>
    );

    expect(screen.getByText('Pantalla de login')).toBeInTheDocument();
    expect(screen.queryByText('Contenido privado')).not.toBeInTheDocument();
  });

  it('muestra el contenido cuando hay sesión', () => {
    useAuthStore.setState({ status: 'authenticated', principal });

    renderProtected(
      <ProtectedRoute>
        <p>Contenido privado</p>
      </ProtectedRoute>
    );

    expect(screen.getByText('Contenido privado')).toBeInTheDocument();
  });

  it('espera sin decidir mientras se restaura la sesión', () => {
    // Redirigir aquí expulsaría a un usuario con sesión válida solo por llegar
    // antes que la respuesta del backend.
    useAuthStore.setState({ status: 'authenticating' });

    renderProtected(
      <ProtectedRoute>
        <p>Contenido privado</p>
      </ProtectedRoute>
    );

    expect(screen.getByLabelText('Verificando sesión')).toBeInTheDocument();
    expect(screen.queryByText('Pantalla de login')).not.toBeInTheDocument();
    expect(screen.queryByText('Contenido privado')).not.toBeInTheDocument();
  });

  it('deniega el acceso si falta el rol exigido', () => {
    useAuthStore.setState({ status: 'authenticated', principal });

    renderProtected(
      <ProtectedRoute requiredRole="admin">
        <p>Contenido privado</p>
      </ProtectedRoute>
    );

    expect(screen.getByText('Acceso denegado')).toBeInTheDocument();
  });

  it('permite el acceso si el rol exigido está presente', () => {
    useAuthStore.setState({ status: 'authenticated', principal });

    renderProtected(
      <ProtectedRoute requiredRole="operator">
        <p>Contenido privado</p>
      </ProtectedRoute>
    );

    expect(screen.getByText('Contenido privado')).toBeInTheDocument();
  });

  it('deniega el acceso si falta el permiso exigido', () => {
    useAuthStore.setState({ status: 'authenticated', principal });

    renderProtected(
      <ProtectedRoute requiredPermission="incidents:delete">
        <p>Contenido privado</p>
      </ProtectedRoute>
    );

    expect(screen.getByText('Acceso denegado')).toBeInTheDocument();
  });

  it('permite el acceso si el permiso exigido está presente', () => {
    useAuthStore.setState({ status: 'authenticated', principal });

    renderProtected(
      <ProtectedRoute requiredPermission="incidents:read">
        <p>Contenido privado</p>
      </ProtectedRoute>
    );

    expect(screen.getByText('Contenido privado')).toBeInTheDocument();
  });
});
