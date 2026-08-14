import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LoginPage } from '@/pages/LoginPage';
import { ApiError } from '@/services';
import { useAuthStore } from '@/store/authStore';
import { renderWithProviders } from '@/test/render';

beforeEach(() => {
  useAuthStore.setState({ status: 'anonymous', principal: null, tokens: null, error: null });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('LoginPage', () => {
  it('presenta campos con etiqueta asociada', () => {
    renderWithProviders(<LoginPage />, { route: '/login' });

    // `getByLabelText` solo encuentra el campo si la etiqueta está realmente
    // asociada: es la comprobación de accesibilidad y de render a la vez.
    expect(screen.getByLabelText(/Usuario/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Contraseña/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument();
  });

  it('envía las credenciales escritas', async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    useAuthStore.setState({ login });

    renderWithProviders(<LoginPage />, { route: '/login' });

    await userEvent.type(screen.getByLabelText(/Usuario/), 'ada');
    await userEvent.type(screen.getByLabelText(/Contraseña/), 'secreto');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));

    expect(login).toHaveBeenCalledWith({ username: 'ada', password: 'secreto' });
  });

  it('muestra el error cuando el backend rechaza las credenciales', async () => {
    const login = vi.fn().mockImplementation(() => {
      useAuthStore.setState({ error: 'Usuario o contraseña incorrectos.' });
      return Promise.reject(
        new ApiError({ type: 'about:blank', title: 'Unauthorized', status: 401 })
      );
    });
    useAuthStore.setState({ login });

    renderWithProviders(<LoginPage />, { route: '/login' });

    await userEvent.type(screen.getByLabelText(/Usuario/), 'ada');
    await userEvent.type(screen.getByLabelText(/Contraseña/), 'mal');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuario o contraseña incorrectos.');
    // El fallo no debe dejar la pantalla inutilizable: se puede reintentar.
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled();
  });

  it('impide el doble envío mientras la petición está en curso', () => {
    useAuthStore.setState({ status: 'authenticating' });

    renderWithProviders(<LoginPage />, { route: '/login' });

    // Sin esto, un doble clic dispara dos logins y el segundo invalida los
    // tokens que acababa de emitir el primero.
    expect(screen.getByRole('button', { name: 'Entrando…' })).toBeDisabled();
  });

  it('no deja escapar el fallo de login como rechazo sin gestionar', async () => {
    const login = vi
      .fn()
      .mockRejectedValue(new ApiError({ type: 'about:blank', title: 'Unauthorized', status: 401 }));
    useAuthStore.setState({ login });
    const unhandled = vi.fn();
    window.addEventListener('unhandledrejection', unhandled);

    renderWithProviders(<LoginPage />, { route: '/login' });
    await userEvent.type(screen.getByLabelText(/Usuario/), 'ada');
    await userEvent.type(screen.getByLabelText(/Contraseña/), 'mal');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));

    await waitFor(() => {
      expect(login).toHaveBeenCalled();
    });
    expect(unhandled).not.toHaveBeenCalled();
    window.removeEventListener('unhandledrejection', unhandled);
  });

  it('redirige a la pantalla pedida cuando ya hay sesión', async () => {
    useAuthStore.setState({ status: 'authenticated' });

    renderWithProviders(<LoginPage />, { route: '/login' });

    // Con sesión abierta, el login no debe seguir mostrándose.
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Entrar' })).not.toBeInTheDocument();
    });
  });
});
