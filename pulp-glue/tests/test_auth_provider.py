import asyncio
import pathlib
from datetime import datetime, timezone

import pytest
from multidict import CIMultiDict
from pydantic.type_adapter import TypeAdapter

from pulp_glue.common import oas
from pulp_glue.common.authentication import (
    AuthProviderBase,
    BasicAuthProvider,
    GlueAuthProvider,
)
from pulp_glue.common.cookie import Cookie

pytestmark = pytest.mark.glue


SECURITY_SCHEMES = TypeAdapter(dict[str, oas.SecurityScheme | oas.Reference]).validate_python(
    {
        "A": {"type": "http", "scheme": "bearer"},
        "B": {"type": "http", "scheme": "basic"},
        "C": {
            "type": "oauth2",
            "flows": {
                "implicit": {
                    "authorizationUrl": "https://example.com/api/oauth/dialog",
                    "scopes": {
                        "write:pets": "modify pets in your account",
                        "read:pets": "read your pets",
                    },
                },
                "authorizationCode": {
                    "authorizationUrl": "https://example.com/api/oauth/dialog",
                    "tokenUrl": "https://example.com/api/oauth/token",
                    "scopes": {
                        "write:pets": "modify pets in your account",
                        "read:pets": "read your pets",
                    },
                },
            },
        },
        "D": {
            "type": "oauth2",
            "flows": {
                "implicit": {
                    "authorizationUrl": "https://example.com/api/oauth/dialog",
                    "scopes": {
                        "write:pets": "modify pets in your account",
                        "read:pets": "read your pets",
                    },
                },
                "clientCredentials": {
                    "tokenUrl": "https://example.com/api/oauth/token",
                    "scopes": {
                        "write:pets": "modify pets in your account",
                        "read:pets": "read your pets",
                    },
                },
            },
        },
        "E": {"type": "mutualTLS"},
        "F": {"type": "apiKey", "in": "cookie", "name": "sessionid"},
    }
)


class TestBasicAuthProvider:
    @pytest.fixture(scope="class")
    def provider(self) -> AuthProviderBase:
        return BasicAuthProvider(username="user1", password="password1")

    def test_can_complete_basic(self, provider: AuthProviderBase) -> None:
        assert provider.can_complete_http_basic()

    def test_provides_username_and_password(self, provider: AuthProviderBase) -> None:
        assert asyncio.run(provider.http_basic_credentials()) == (
            b"user1",
            b"password1",
        )

    def test_cannot_complete_mutualTLS(self, provider: AuthProviderBase) -> None:
        assert not provider.can_complete_mutualTLS()

    def test_can_complete_basic_proposal(self, provider: AuthProviderBase) -> None:
        assert provider.can_complete({"B": []}, security_schemes=SECURITY_SCHEMES)

    def test_cannot_complete_bearer_proposal(self, provider: AuthProviderBase) -> None:
        assert not provider.can_complete({"A": []}, security_schemes=SECURITY_SCHEMES)

    def test_cannot_complete_combined_proposal(self, provider: AuthProviderBase) -> None:
        assert not provider.can_complete({"A": [], "B": []}, security_schemes=SECURITY_SCHEMES)


class TestGlueAuthProvider:
    def test_empty_provider_cannot_complete(self) -> None:
        provider = GlueAuthProvider()
        assert provider.can_complete_http_basic() is False
        assert provider.can_complete_oauth2_client_credentials([]) is False
        assert provider.can_complete_mutualTLS() is False

    def test_username_needs_password(self) -> None:
        with pytest.raises(AssertionError):
            GlueAuthProvider(username="user1")

    def test_can_complete_basic_auth_and_provide_credentials(self) -> None:
        provider = GlueAuthProvider(username="user1", password="secret1")
        assert provider.can_complete_http_basic() == 15
        assert asyncio.run(provider.http_basic_credentials()) == (b"user1", b"secret1")

    def test_can_complete_api_key(self) -> None:
        provider = GlueAuthProvider(api_key="test_api_key_123")
        scheme = SECURITY_SCHEMES["F"]
        assert isinstance(scheme, oas.SecuritySchemeApiKey)
        assert provider.can_complete({"F": []}, security_schemes=SECURITY_SCHEMES)
        assert asyncio.run(provider.api_key_credentials(scheme)) == "test_api_key_123"

    def test_client_id_needs_client_secret(self) -> None:
        with pytest.raises(AssertionError):
            GlueAuthProvider(client_id="client1")

    def test_can_complete_oauth2_client_credentials_and_provide_them(self) -> None:
        provider = GlueAuthProvider(client_id="client1", client_secret="secret1")
        assert provider.can_complete_oauth2_client_credentials([]) == 10
        assert asyncio.run(provider.oauth2_client_credentials()) == (
            b"client1",
            b"secret1",
        )

    def test_can_complete_mutualTLS_and_provide_cert(self) -> None:
        provider = GlueAuthProvider(cert="FAKECERTIFICATE")
        assert provider.can_complete_mutualTLS() == 0
        assert provider.tls_credentials() == ("FAKECERTIFICATE", None)

    def test_extracts_cookies(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
        provider = GlueAuthProvider()
        headers = CIMultiDict(
            (
                ("content-type", "text/plain"),
                (
                    "set-cookie",
                    "csrftoken=C3gBQ0SMgEJR6FCMUpy3Hf3iXfhkA17B; expires=Wed, 26 May 2027 13:22:50 GMT; Max-Age=31449600; Path=/; SameSite=Lax",
                ),
                (
                    "set-cookie",
                    "sessionid=1kj1jdpk750wvff7yrda30pa07tzqr4a; expires=Wed, 10 Jun 2026 13:22:50 GMT; HttpOnly; Max-Age=1209600; Path=/; SameSite=Lax",
                ),
            )
        )
        asyncio.run(provider.response_headers_hook(headers))

        assert provider._cookiejar == {
            "csrftoken": Cookie(
                name="csrftoken",
                value="C3gBQ0SMgEJR6FCMUpy3Hf3iXfhkA17B",
                expires=datetime(2027, 5, 26, 13, 22, 50, tzinfo=timezone.utc),
                http_only=False,
                same_site="Lax",
                path="/",
            ),
            "sessionid": Cookie(
                name="sessionid",
                value="1kj1jdpk750wvff7yrda30pa07tzqr4a",
                expires=datetime(2026, 6, 10, 13, 22, 50, tzinfo=timezone.utc),
                http_only=True,
                same_site="Lax",
                path="/",
            ),
        }
