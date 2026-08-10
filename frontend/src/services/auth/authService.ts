import type { AuthEndpoints } from '@/config';
import type { HttpClient } from '@/services/http/client';
import type { Credentials, Principal, TokenPair } from '@/types/auth';

/**
 * Operaciones de sesión contra la aplicación anfitriona.
 *
 * Las rutas llegan por constructor y no cableadas: **TEAF no expone endpoints
 * de login** (ADR-013). El framework entrega `JWTTokenProvider`, `IdentityProvider`
 * y RBAC; qué ruta emite el `TokenPair` lo decide cada aplicación. Así el mismo
 * servicio sirve a TicketGateway, Portal NOC y Portal SRE aunque publiquen rutas
 * distintas.
 */
export class AuthService {
  private readonly http: HttpClient;
  private readonly endpoints: AuthEndpoints;

  constructor(http: HttpClient, endpoints: AuthEndpoints) {
    this.http = http;
    this.endpoints = endpoints;
  }

  /** Canjea credenciales por un `TokenPair`. */
  login(credentials: Credentials): Promise<TokenPair> {
    return this.http.post<TokenPair>(this.endpoints.login, credentials);
  }

  /**
   * Canjea el refresh token por un par nuevo.
   *
   * El backend revoca el refresh token usado al emitir el nuevo (rotación, ver
   * `JWTTokenProvider.refresh`), así que el par devuelto reemplaza al anterior
   * por completo: conservar el viejo lo dejaría inservible.
   */
  refresh(refreshToken: string): Promise<TokenPair> {
    return this.http.post<TokenPair>(this.endpoints.refresh, { refreshToken });
  }

  /**
   * Cierra la sesión en el servidor.
   *
   * No lanza: si el logout remoto falla, la sesión local se limpia igualmente.
   * Dejar al usuario dentro porque el servidor no contestó es peor que la
   * revocación pendiente que el token resolverá al expirar.
   */
  async logout(): Promise<void> {
    try {
      await this.http.post<void>(this.endpoints.logout);
    } catch {
      // Intencionadamente silencioso — ver docstring.
    }
  }

  /** Recupera el `Principal` (identidad + roles + permisos) de la sesión en curso. */
  currentPrincipal(): Promise<Principal> {
    return this.http.get<Principal>(this.endpoints.me);
  }
}
