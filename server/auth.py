"""
Authentication module for ERCOT API

Handles token acquisition, caching, and automatic refresh.
Converted from tokenstorage.jl and ErcotMagic.jl:get_auth_token()
"""

import os
from datetime import datetime, timedelta
from typing import Optional
import requests
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
except ImportError:
    # dotenv is optional - only needed for local development
    def load_dotenv():
        pass


class ErcotToken(BaseModel):
    """Token storage model matching Julia's ErcotToken struct"""

    expires_in: str = ""
    token_type: str = ""
    refresh_token: str = ""
    id_token: str = ""
    access_token: str = ""
    acquired_at: datetime = datetime.now()

    class Config:
        arbitrary_types_allowed = True


class ErcotAuth:
    """
    ERCOT API authentication manager with automatic token refresh.

    Source: tokenstorage.jl and ErcotMagic.jl:91-106

    Usage:
        auth = ErcotAuth()
        token = auth.get_valid_token()
    """

    AUTH_URL = "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
    CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"
    SCOPE = "openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access"
    TOKEN_LIFETIME = timedelta(hours=1)

    def __init__(self):
        """Initialize authentication manager and load credentials from environment"""
        # Try to load from .env file (for local development)
        # This will silently do nothing if .env doesn't exist
        load_dotenv()

        # Get credentials from environment variables
        # When used as MCP extension, these are passed from user_config in manifest.json
        self.username = os.getenv("ERCOTUSER")
        self.password = os.getenv("ERCOTPASS")

        if not self.username or not self.password:
            raise ValueError(
                "ERCOT API credentials not found. "
                "When using as MCP extension, configure credentials in extension settings. "
                "When using standalone, set ERCOTUSER and ERCOTPASS environment variables or create a .env file."
            )

        self._token: Optional[ErcotToken] = None

    def get_auth_token(self) -> dict:
        """
        Retrieve authentication token from ERCOT API using ROPC flow.

        Source: ErcotMagic.jl:91-106

        Returns:
            dict: Token response containing id_token, access_token, etc.

        Raises:
            requests.HTTPError: If authentication fails
        """
        params = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "response_type": "id_token",
            "scope": self.SCOPE,
            "client_id": self.CLIENT_ID,
        }

        try:
            response = requests.post(
                self.AUTH_URL,
                data=params,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError(
                    "Authentication failed. Check your ERCOTUSER and ERCOTPASS credentials."
                ) from e
            raise
        except requests.exceptions.Timeout:
            raise TimeoutError("Authentication request timed out") from None

    def fetch_new_token(self) -> ErcotToken:
        """
        Fetch a new token and wrap in ErcotToken model.

        Source: tokenstorage.jl:14-19

        Returns:
            ErcotToken: Newly acquired token with timestamp
        """
        token_data = self.get_auth_token()
        token_data["acquired_at"] = datetime.now()
        return ErcotToken(**token_data)

    def is_token_valid(self) -> bool:
        """
        Check if current token is still valid.

        Source: tokenstorage.jl:22-32

        Returns:
            bool: True if token exists and hasn't expired
        """
        if self._token is None or not self._token.id_token:
            return False

        time_since_acquired = datetime.now() - self._token.acquired_at
        return time_since_acquired < self.TOKEN_LIFETIME

    def get_valid_token(self) -> str:
        """
        Get a valid token, fetching a new one if necessary.

        Source: tokenstorage.jl:22-36

        This method automatically handles token expiration and refresh.
        Tokens are valid for 1 hour.

        Returns:
            str: Valid id_token ready for API calls
        """
        if not self.is_token_valid():
            self._token = self.fetch_new_token()

        return self._token.id_token

    def get_auth_headers(self) -> dict:
        """
        Get headers dict with valid authentication token.

        Returns:
            dict: Headers ready for use in API requests
        """
        return {"Authorization": f"Bearer {self.get_valid_token()}"}


# Global instance for convenience (matching Julia's global pattern)
_global_auth: Optional[ErcotAuth] = None


def get_global_auth() -> ErcotAuth:
    """Get or create global authentication instance"""
    global _global_auth
    if _global_auth is None:
        _global_auth = ErcotAuth()
    return _global_auth
