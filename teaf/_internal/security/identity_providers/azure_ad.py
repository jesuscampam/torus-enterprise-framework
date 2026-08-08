"""``AzureADIdentityProvider`` — Microsoft Entra ID (Azure AD), vía OIDC/OAuth2.

Especialización concreta de ``OpenIDConnectIdentityProvider`` — la prueba
viva de que Keycloak/Auth0/Okta/Google (ver ADR-007) pueden reutilizar la
misma base sin rediseño: solo fija las URLs de ``login.microsoftonline.com``
y mapea los claims específicos de Azure AD (``oid``, ``tid``,
``preferred_username``, ``roles``, ``groups``).
"""

from __future__ import annotations

from typing import Any

import httpx

from teaf._internal.security.exceptions import OidcException
from teaf._internal.security.identity_providers.oidc import (
    OidcDiscoveryDocument,
    OpenIDConnectIdentityProvider,
)
from teaf._internal.security.models import Claims

#: Valores de ``tenant`` que Microsoft trata como "multi-tenant" — el
#: documento de descubrimiento resultante tiene un ``issuer`` con el
#: placeholder literal ``{tenantid}``, así que no se puede validar como
#: cadena exacta (ver ``_issuer_for_validation``).
_MULTI_TENANT_VALUES = frozenset({"common", "organizations", "consumers"})


class AzureADIdentityProvider(OpenIDConnectIdentityProvider):
    """Valida tokens emitidos por Microsoft Entra ID (Azure AD) y resuelve la identidad."""

    def __init__(
        self,
        *,
        tenant: str,
        client_id: str,
        client_secret: str | None = None,
        allowed_tenants: frozenset[str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """``tenant`` es el tenant de Azure AD (un GUID) o uno de
        ``"common"``/``"organizations"``/``"consumers"`` para multi-tenant.
        ``allowed_tenants``, cuando se usa un valor multi-tenant, restringe
        qué tenants concretos (claim ``tid``) se aceptan — sin esto,
        cualquier tenant de Azure AD podría autenticarse contra esta
        aplicación."""
        discovery_url = (
            f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"
        )
        super().__init__(
            provider_id="azure-ad",
            discovery_url=discovery_url,
            client_id=client_id,
            client_secret=client_secret,
            http_client=http_client,
        )
        self._tenant = tenant
        self._allowed_tenants = allowed_tenants

    def _issuer_for_validation(self, discovery: OidcDiscoveryDocument) -> str | None:
        """Omite la validación estricta de ``iss`` en modo multi-tenant.

        El documento de descubrimiento "común" tiene ``issuer`` con el
        placeholder literal ``{tenantid}`` sin resolver — el tenant real
        del token se valida después, sobre el claim ``tid`` (ver
        ``_map_claims``), no comparando el ``issuer``.
        """
        if self._tenant in _MULTI_TENANT_VALUES:
            return None
        return discovery.issuer

    def _map_claims(self, payload: dict[str, Any]) -> Claims:
        """Mapea claims de Azure AD: ``oid`` (más estable que ``sub``), ``tid``,
        ``preferred_username`` (email), ``roles``/``groups`` (App Roles/grupos,
        si la aplicación de Azure AD está configurada para emitirlos)."""
        tenant_id = payload.get("tid")
        if self._allowed_tenants is not None and tenant_id not in self._allowed_tenants:
            raise OidcException(
                f"Tenant de Azure AD '{tenant_id}' no está en la lista de tenants permitidos."
            )
        subject = payload.get("oid") or payload["sub"]
        return Claims(
            sub=subject,
            name=payload.get("name"),
            email=payload.get("preferred_username") or payload.get("email"),
            tenant=tenant_id,
            roles=frozenset(payload.get("roles") or ()),
            groups=frozenset(payload.get("groups") or ()),
            extra=payload,
        )
