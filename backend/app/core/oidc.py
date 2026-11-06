"""OIDC/Keycloak integration for authentication."""
import httpx
from typing import Optional
from fastapi import HTTPException, status
from jose import jwt, JWTError
from app.core.config import get_settings

settings = get_settings()


class OIDCClient:
    """Client for interacting with Keycloak OIDC endpoints."""

    def __init__(self):
        self.keycloak_url = settings.keycloak_url.rstrip("/")
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self._jwks_cache: Optional[dict] = None
        self._well_known_cache: Optional[dict] = None

    @property
    def well_known_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/.well-known/openid-configuration"

    @property
    def jwks_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"

    @property
    def auth_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/auth"

    @property
    def token_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"

    @property
    def userinfo_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/userinfo"

    @property
    def logout_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/logout"

    async def get_well_known(self) -> dict:
        """Fetch OIDC well-known configuration."""
        if self._well_known_cache is None:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.well_known_url, timeout=10.0)
                response.raise_for_status()
                self._well_known_cache = response.json()
        return self._well_known_cache

    async def get_jwks(self) -> dict:
        """Fetch JSON Web Key Set for token verification."""
        if self._jwks_cache is None:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url, timeout=10.0)
                response.raise_for_status()
                self._jwks_cache = response.json()
        return self._jwks_cache

    async def verify_id_token(self, id_token: str) -> dict:
        """Verify an ID token using Keycloak's JWKS."""
        jwks = await self.get_jwks()

        # Find the matching key
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token header: missing kid",
            )

        key = None
        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching key",
            )

        try:
            payload = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                options={"verify_aud": True},
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}",
            )

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for access/ID tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {response.text}",
                )
            return response.json()

    async def get_userinfo(self, access_token: str) -> dict:
        """Get user info from Keycloak."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    def get_auth_url(self, redirect_uri: str, state: str, nonce: str = "") -> str:
        """Generate Keycloak authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        if nonce:
            params["nonce"] = nonce

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.auth_url}?{query}"

    def get_logout_url(self, redirect_uri: str) -> str:
        """Generate Keycloak logout URL."""
        params = {
            "client_id": self.client_id,
            "post_logout_redirect_uri": redirect_uri,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.logout_url}?{query}"


# Global OIDC client instance
oidc_client = OIDCClient()

