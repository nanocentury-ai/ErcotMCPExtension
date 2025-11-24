"""
Tests for authentication module

Tests converted from Julia package behavior
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import os
import requests

from ercot_mcp.auth import ErcotAuth, ErcotToken


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    with patch.dict(os.environ, {
        "ERCOTUSER": "test_user",
        "ERCOTPASS": "test_pass"
    }):
        yield


@pytest.fixture
def mock_token_response():
    """Mock successful token response"""
    return {
        "id_token": "test_id_token_123",
        "access_token": "test_access_token_456",
        "token_type": "Bearer",
        "expires_in": "3600",
        "refresh_token": "test_refresh_token_789"
    }


class TestErcotToken:
    """Test ErcotToken model"""

    def test_token_creation(self):
        """Test token model creation"""
        token = ErcotToken(
            id_token="test_token",
            access_token="test_access",
            acquired_at=datetime.now()
        )
        assert token.id_token == "test_token"
        assert token.access_token == "test_access"
        assert isinstance(token.acquired_at, datetime)

    def test_token_defaults(self):
        """Test token default values"""
        token = ErcotToken()
        assert token.id_token == ""
        assert token.expires_in == ""
        assert isinstance(token.acquired_at, datetime)


class TestErcotAuth:
    """Test ErcotAuth authentication manager"""

    @patch('ercot_mcp.auth.load_dotenv')
    def test_init_requires_credentials(self, mock_load_dotenv):
        """Test that initialization requires credentials"""
        # Clear environment variables to test missing credentials
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ERCOTUSER and ERCOTPASS"):
                ErcotAuth()

    def test_init_with_credentials(self, mock_env):
        """Test successful initialization with credentials"""
        auth = ErcotAuth()
        assert auth.username == "test_user"
        assert auth.password == "test_pass"

    @patch('ercot_mcp.auth.requests.post')
    def test_get_auth_token_success(self, mock_post, mock_env, mock_token_response):
        """Test successful token acquisition"""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Call
        auth = ErcotAuth()
        result = auth.get_auth_token()

        # Verify
        assert result["id_token"] == "test_id_token_123"
        assert result["access_token"] == "test_access_token_456"
        mock_post.assert_called_once()

        # Check correct parameters were sent
        call_kwargs = mock_post.call_args
        assert "data" in call_kwargs[1]
        assert call_kwargs[1]["data"]["username"] == "test_user"
        assert call_kwargs[1]["data"]["password"] == "test_pass"

    @patch('ercot_mcp.auth.requests.post')
    def test_get_auth_token_401_error(self, mock_post, mock_env):
        """Test handling of authentication failure"""
        # Setup mock for 401 error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        # Create proper HTTPError with response object
        http_error = requests.exceptions.HTTPError("401 Client Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error

        auth = ErcotAuth()

        with pytest.raises(ValueError, match="Authentication failed"):
            auth.get_auth_token()

    @patch('ercot_mcp.auth.requests.post')
    def test_fetch_new_token(self, mock_post, mock_env, mock_token_response):
        """Test fetch_new_token wraps token in ErcotToken model"""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Call
        auth = ErcotAuth()
        token = auth.fetch_new_token()

        # Verify
        assert isinstance(token, ErcotToken)
        assert token.id_token == "test_id_token_123"
        assert isinstance(token.acquired_at, datetime)

    def test_is_token_valid_no_token(self, mock_env):
        """Test token validation when no token exists"""
        auth = ErcotAuth()
        assert not auth.is_token_valid()

    def test_is_token_valid_fresh_token(self, mock_env):
        """Test token validation with fresh token"""
        auth = ErcotAuth()
        auth._token = ErcotToken(
            id_token="test_token",
            acquired_at=datetime.now()
        )
        assert auth.is_token_valid()

    def test_is_token_valid_expired_token(self, mock_env):
        """Test token validation with expired token (>1 hour old)"""
        auth = ErcotAuth()
        auth._token = ErcotToken(
            id_token="test_token",
            acquired_at=datetime.now() - timedelta(hours=2)
        )
        assert not auth.is_token_valid()

    @patch('ercot_mcp.auth.requests.post')
    def test_get_valid_token_fetches_when_none(self, mock_post, mock_env, mock_token_response):
        """Test get_valid_token fetches new token when none exists"""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Call
        auth = ErcotAuth()
        token = auth.get_valid_token()

        # Verify
        assert token == "test_id_token_123"
        mock_post.assert_called_once()

    @patch('ercot_mcp.auth.requests.post')
    def test_get_valid_token_reuses_valid_token(self, mock_post, mock_env, mock_token_response):
        """Test get_valid_token reuses valid token without new API call"""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Call twice
        auth = ErcotAuth()
        token1 = auth.get_valid_token()
        token2 = auth.get_valid_token()

        # Verify
        assert token1 == token2
        # Should only be called once (not twice)
        assert mock_post.call_count == 1

    def test_get_auth_headers(self, mock_env):
        """Test auth headers generation"""
        auth = ErcotAuth()
        auth._token = ErcotToken(
            id_token="test_token_123",
            acquired_at=datetime.now()
        )

        headers = auth.get_auth_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token_123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
