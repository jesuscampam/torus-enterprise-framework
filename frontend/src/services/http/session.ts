/**
 * Puente entre el cliente HTTP y quien gestiona la sesión.
 *
 * Existe para romper una dependencia circular real: el `HttpClient` necesita el
 * access token y saber cómo renovarlo; quien tiene ambas cosas es el store de
 * autenticación, que a su vez usa el `HttpClient` para hacer login.
 *
 * La solución es la misma que en backend: **el que está más adentro define el
 * contrato y el de fuera lo satisface**. El cliente depende de este puente
 * (sencillo, sin dependencias); el store se registra en él al arrancar. Así la
 * dependencia apunta hacia adentro y ningún módulo importa al otro
 * (ARCHITECTURE.md, regla no negociable de dirección de dependencias).
 */
export class SessionBridge {
  private accessToken: string | null = null;
  private refreshHandler: (() => Promise<string | null>) | null = null;

  /** Lo consume `HttpClient.getAccessToken`. Campo-flecha: se pasa suelto sin perder `this`. */
  readonly getAccessToken = (): string | null => this.accessToken;

  /** Lo consume `HttpClient.refreshAccessToken` ante un 401. */
  readonly refreshAccessToken = async (): Promise<string | null> => {
    if (!this.refreshHandler) return null;
    return this.refreshHandler();
  };

  /** El store publica aquí el token vigente en cada cambio de sesión. */
  setAccessToken(token: string | null): void {
    this.accessToken = token;
  }

  /** El store registra aquí cómo renovar la sesión. */
  setRefreshHandler(handler: (() => Promise<string | null>) | null): void {
    this.refreshHandler = handler;
  }
}
