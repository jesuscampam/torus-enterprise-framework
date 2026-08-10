import type { TokenPair } from '@/types/auth';

/**
 * Dónde viven los tokens de la sesión.
 *
 * Mismo patrón provider que `CacheProvider` (ADR-012) y `SecretProvider` en
 * backend: el framework define el contrato y entrega implementaciones; la
 * decisión de cuál usar es de la aplicación, porque depende de su modelo de
 * despliegue (ADR-013 §5).
 */
export interface TokenStorage {
  read(): TokenPair | null;
  write(tokens: TokenPair): void;
  clear(): void;
  readonly name: string;
}

/**
 * Tokens solo en memoria. **Implementación por defecto.**
 *
 * Es la resistente a XSS: un script inyectado no encuentra nada en
 * `localStorage` porque no hay nada. El precio es que la sesión se pierde al
 * recargar la página. El arranque seguro es el defecto; relajarlo es un acto
 * explícito de la aplicación (SECURITY-STANDARD.md §2).
 */
export class MemoryTokenStorage implements TokenStorage {
  readonly name = 'memory';
  private tokens: TokenPair | null = null;

  read(): TokenPair | null {
    return this.tokens;
  }

  write(tokens: TokenPair): void {
    this.tokens = tokens;
  }

  clear(): void {
    this.tokens = null;
  }
}

/**
 * Tokens en `localStorage`, de modo que la sesión sobreviva a la recarga.
 *
 * **Opt-in consciente**: cualquier script que se ejecute en la página puede
 * leerlos. Solo tiene sentido cuando la aplicación acepta ese riesgo a cambio
 * de la comodidad. Si el backend puede emitir cookies `httpOnly`, esa vía es
 * preferible a esta.
 */
export class LocalStorageTokenStorage implements TokenStorage {
  readonly name = 'localStorage';
  private readonly key: string;

  constructor(key = 'teaf.auth.tokens') {
    this.key = key;
  }

  read(): TokenPair | null {
    try {
      const raw = window.localStorage.getItem(this.key);
      if (!raw) return null;

      const parsed: unknown = JSON.parse(raw);
      if (typeof parsed !== 'object' || parsed === null) return null;

      const candidate = parsed as Partial<TokenPair>;
      if (typeof candidate.accessToken !== 'string') return null;
      if (typeof candidate.refreshToken !== 'string') return null;

      return {
        accessToken: candidate.accessToken,
        refreshToken: candidate.refreshToken,
        tokenType: candidate.tokenType ?? 'Bearer',
        expiresIn: candidate.expiresIn ?? 0,
      };
    } catch {
      // localStorage puede no existir (SSR, modo privado) o traer basura de una
      // versión anterior: en ambos casos equivale a no tener sesión.
      return null;
    }
  }

  write(tokens: TokenPair): void {
    try {
      window.localStorage.setItem(this.key, JSON.stringify(tokens));
    } catch {
      // Cuota llena o almacenamiento bloqueado: la sesión sigue viva en memoria
      // dentro del store, solo no sobrevivirá a la recarga.
    }
  }

  clear(): void {
    try {
      window.localStorage.removeItem(this.key);
    } catch {
      // Nada que hacer: no poder borrar no debe impedir cerrar sesión.
    }
  }
}
