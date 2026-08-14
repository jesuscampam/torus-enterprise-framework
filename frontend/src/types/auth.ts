/**
 * Tipos de autenticación, espejo del modelo de dominio de seguridad que TEAF
 * publica en `teaf.security` (`TokenPair`, `Principal`, `Identity`, `Claims`),
 * decidido en [ADR-007](../../../docs/architecture/adr/ADR-007-enterprise-security-stack.md).
 *
 * La referencia es a la **superficie pública** a propósito: el frontend es un
 * consumidor externo y no debe seguirle la pista a `teaf._internal`, cuya forma
 * puede cambiar sin previo aviso ([PUBLIC-API.md](../../../docs/public-api/PUBLIC-API.md)).
 *
 * La correspondencia es literal: `TokenPair` aquí tiene los mismos cuatro
 * campos que emite `TokenPair.as_dict()` allí, en el mismo camelCase.
 */

/**
 * Par de tokens emitido por el backend tras un login o un refresh.
 *
 * Corresponde exactamente a `TokenPair.as_dict()` del backend:
 * `{accessToken, refreshToken, tokenType, expiresIn}`.
 */
export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  /** Vida del access token en segundos (por defecto 900 en el backend). */
  expiresIn: number;
}

/** Claims de identidad — espejo de `Claims` del backend. */
export interface Claims {
  subject: string;
  name?: string;
  email?: string;
  [claim: string]: unknown;
}

/**
 * Quién es el llamante — espejo de `Identity` del backend.
 *
 * Responde «quién eres», nunca «qué puedes hacer»: eso es `Principal`.
 */
export interface Identity {
  id: string;
  providerId: string;
  claims: Claims;
  authenticated: boolean;
}

/**
 * El sujeto de autorización — espejo de `Principal` del backend.
 *
 * `Identity` con roles, permisos y tenant ya resueltos. La separación entre
 * ambos es la misma que sostiene el motor de autorización del backend.
 */
export interface Principal {
  identity: Identity;
  roles: string[];
  permissions: string[];
  tenantId?: string;
}

/** Credenciales de un login por usuario y contraseña. */
export interface Credentials {
  username: string;
  password: string;
}

/** Estado de la sesión, tal como lo expone el store de autenticación. */
export type AuthStatus = 'anonymous' | 'authenticating' | 'authenticated';
