import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { TokenPair } from '@/types/auth';

import { LocalStorageTokenStorage, MemoryTokenStorage } from './tokenStorage';

const tokens: TokenPair = {
  accessToken: 'access-1',
  refreshToken: 'refresh-1',
  tokenType: 'Bearer',
  expiresIn: 900,
};

describe('MemoryTokenStorage', () => {
  it('empieza vacío', () => {
    expect(new MemoryTokenStorage().read()).toBeNull();
  });

  it('devuelve lo que se escribió', () => {
    const storage = new MemoryTokenStorage();
    storage.write(tokens);
    expect(storage.read()).toEqual(tokens);
  });

  it('queda vacío tras limpiar', () => {
    const storage = new MemoryTokenStorage();
    storage.write(tokens);
    storage.clear();
    expect(storage.read()).toBeNull();
  });

  it('no deja rastro en localStorage — es la razón de ser de esta implementación', () => {
    new MemoryTokenStorage().write(tokens);
    expect(window.localStorage.length).toBe(0);
  });
});

describe('LocalStorageTokenStorage', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('persiste y recupera el par de tokens', () => {
    const storage = new LocalStorageTokenStorage();
    storage.write(tokens);
    expect(storage.read()).toEqual(tokens);
  });

  it('una instancia nueva ve lo que persistió la anterior', () => {
    new LocalStorageTokenStorage().write(tokens);
    expect(new LocalStorageTokenStorage().read()).toEqual(tokens);
  });

  it('borra la entrada al limpiar', () => {
    const storage = new LocalStorageTokenStorage();
    storage.write(tokens);
    storage.clear();
    expect(storage.read()).toBeNull();
    expect(window.localStorage.length).toBe(0);
  });

  it('devuelve null si el contenido almacenado no es JSON válido', () => {
    window.localStorage.setItem('teaf.auth.tokens', 'no-es-json{');
    expect(new LocalStorageTokenStorage().read()).toBeNull();
  });

  it('devuelve null si falta accessToken — dato de una versión anterior', () => {
    window.localStorage.setItem('teaf.auth.tokens', JSON.stringify({ refreshToken: 'r' }));
    expect(new LocalStorageTokenStorage().read()).toBeNull();
  });

  it('completa tokenType y expiresIn ausentes con valores por defecto', () => {
    window.localStorage.setItem(
      'teaf.auth.tokens',
      JSON.stringify({ accessToken: 'a', refreshToken: 'r' })
    );

    expect(new LocalStorageTokenStorage().read()).toEqual({
      accessToken: 'a',
      refreshToken: 'r',
      tokenType: 'Bearer',
      expiresIn: 0,
    });
  });

  it('no propaga el error si localStorage rechaza la escritura (cuota llena)', () => {
    const storage = new LocalStorageTokenStorage();
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });

    expect(() => storage.write(tokens)).not.toThrow();
    vi.restoreAllMocks();
  });

  it('respeta una clave personalizada', () => {
    new LocalStorageTokenStorage('app.tokens').write(tokens);
    expect(window.localStorage.getItem('app.tokens')).toBeTruthy();
    expect(window.localStorage.getItem('teaf.auth.tokens')).toBeNull();
  });
});
