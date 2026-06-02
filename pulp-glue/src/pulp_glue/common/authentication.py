import os
import typing as t
import warnings
from datetime import datetime, timezone
from pathlib import Path

from multidict import CIMultiDict

from pulp_glue.common import oas
from pulp_glue.common.cookie import Cookie, cookiejar_adapter


class AuthProviderBase:
    """
    Base class for auth providers.

    This abstract base class will analyze the authentication proposals of the openapi specs.
    Different authentication schemes can be implemented in subclasses.
    """

    def can_complete_http_basic(self) -> t.Literal[False] | int:
        return False

    def can_complete_api_key(
        self, security_scheme: oas.SecuritySchemeApiKey
    ) -> t.Literal[False] | int:
        return False

    def can_complete_mutualTLS(self) -> t.Literal[False] | int:
        return False

    def can_complete_oauth2_client_credentials(self, scopes: list[str]) -> t.Literal[False] | int:
        return False

    def can_complete_scheme(
        self, security_scheme: oas.SecurityScheme, scopes: list[str]
    ) -> t.Literal[False] | int:
        if isinstance(security_scheme, oas.SecuritySchemeHttp):
            if security_scheme.scheme == "basic":
                return self.can_complete_http_basic()
        elif isinstance(security_scheme, oas.SecuritySchemeApiKey):
            return self.can_complete_api_key(security_scheme)
        elif isinstance(security_scheme, oas.SecuritySchemeMutualTLS):
            return self.can_complete_mutualTLS()
        elif isinstance(security_scheme, oas.SecuritySchemeOAuth2):
            client_credentials_flow = security_scheme.flows.client_credentials
            if client_credentials_flow is not None:
                return self.can_complete_oauth2_client_credentials(
                    list(client_credentials_flow.scopes.keys())
                )
        return False

    def can_complete(
        self,
        proposal: dict[str, list[str]],
        security_schemes: dict[str, oas.SecurityScheme | oas.Reference],
    ) -> t.Literal[False] | int:
        cost: int = 0
        for name, scopes in proposal.items():
            security_scheme = security_schemes.get(name)
            if security_scheme is None:
                warnings.warn("OpenAPI references security scheme it does not define.")
                return False
            if isinstance(security_scheme, oas.Reference):
                # TODO implement dereferencing in the authenticating code first.
                return False
            if (extra_cost := self.can_complete_scheme(security_scheme, scopes)) is False:
                return False
            cost += extra_cost
        # This covers the case where `[]` allows for no auth at all for zero cost.
        return cost

    async def auth_success_hook(self, **kwargs: t.Any) -> None:
        pass

    async def auth_failure_hook(self, **kwargs: t.Any) -> None:
        pass

    async def response_headers_hook(self, headers: CIMultiDict[str]) -> None:
        pass

    def csrftoken(self) -> str:
        raise NotImplementedError()

    async def http_basic_credentials(self) -> tuple[bytes, bytes]:
        raise NotImplementedError()

    async def api_key_credentials(self, security_scheme: oas.SecuritySchemeApiKey) -> str:
        raise NotImplementedError()

    async def oauth2_client_credentials(self) -> tuple[bytes, bytes]:
        raise NotImplementedError()

    def tls_credentials(self) -> tuple[str, str | None]:
        raise NotImplementedError()


class BasicAuthProvider(AuthProviderBase):
    """
    AuthProvider providing basic auth with fixed `username`, `password`.
    """

    def __init__(self, username: t.AnyStr, password: t.AnyStr):
        super().__init__()
        self.username: bytes = username.encode("latin1") if isinstance(username, str) else username
        self.password: bytes = password.encode("latin1") if isinstance(password, str) else password

    def can_complete_http_basic(self) -> t.Literal[False] | int:
        return 1

    async def http_basic_credentials(self) -> tuple[bytes, bytes]:
        return self.username, self.password


class GlueAuthProvider(AuthProviderBase):
    """
    AuthProvider allowing to be used with prepared credentials.
    """

    def __init__(
        self,
        *,
        username: t.AnyStr | None = None,
        password: t.AnyStr | None = None,
        api_key: str | None = None,
        client_id: t.AnyStr | None = None,
        client_secret: t.AnyStr | None = None,
        cert: str | None = None,
        key: str | None = None,
    ):
        super().__init__()
        self.username: bytes | None = None
        self.password: bytes | None = None
        self.api_key: str | None = api_key
        self.client_id: bytes | None = None
        self.client_secret: bytes | None = None
        self.cert: str | None = cert
        self.key: str | None = key

        if username is not None:
            assert password is not None
            self.username = username.encode("latin1") if isinstance(username, str) else username
            self.password = password.encode("latin1") if isinstance(password, str) else password
        if client_id is not None:
            assert client_secret is not None
            self.client_id = client_id.encode("latin1") if isinstance(client_id, str) else client_id
            self.client_secret = (
                client_secret.encode("latin1") if isinstance(client_secret, str) else client_secret
            )

        if cert is None and key is not None:
            raise RuntimeError("Key can only be used together with a cert.")

        # This class also acts as a cookiejar for authentication.
        self._cookiejar: dict[str, Cookie] = {}
        self._load_cookies()

    def _expire_cookies(self) -> None:
        now = datetime.now(timezone.utc)
        self._cookiejar = {
            n: c for n, c in self._cookiejar.items() if c.expires is not None and c.expires > now
        }

    def _load_cookies(self) -> None:
        if (xdg_runtime_dir := os.environ.get("XDG_RUNTIME_DIR")) is not None:
            cookiejar_path = Path(xdg_runtime_dir) / "pulp_cookiejar"
            try:
                cookies = cookiejar_adapter.validate_json(cookiejar_path.read_bytes())
                for c in cookies:
                    self._cookiejar[c.name] = c
            except (OSError, ValueError):
                pass

    def _store_cookies(self) -> None:
        if (xdg_runtime_dir := os.environ.get("XDG_RUNTIME_DIR")) is not None:
            cookiejar_path = Path(xdg_runtime_dir) / "pulp_cookiejar"
            try:
                cookies = [c for c in self._cookiejar.values()]
                cookiejar_path.write_bytes(cookiejar_adapter.dump_json(cookies))
            except (OSError, ValueError):
                pass

    async def response_headers_hook(self, headers: CIMultiDict[str]) -> None:
        # Update CookieJar.
        changed = False
        for ch in headers.getall("set-cookie", []):
            c = Cookie.from_header(ch)
            old_c = self._cookiejar.get(c.name)
            if c.value == "" or c.value == '""':
                if old_c is not None:
                    self._cookiejar.pop(c.name)
                    changed = True
            elif c != old_c:
                self._cookiejar[c.name] = c
                changed = True
        if changed:
            self._store_cookies()

    def csrftoken(self) -> str:
        if (c := self._cookiejar.get("csrftoken")) is None:
            raise RuntimeError("No csrftoken available.")
        return c.value

    def can_complete_http_basic(self) -> t.Literal[False] | int:
        # Basic auth is comparatively costly on the server side.
        return self.username is not None and 15

    def can_complete_api_key(
        self, security_scheme: oas.SecuritySchemeApiKey
    ) -> t.Literal[False] | int:
        if security_scheme.in_ == "cookie":
            self._expire_cookies()
            if security_scheme.name in self._cookiejar:
                # We seem to have the session cookie, so no extra cost.
                return 0
        return self.api_key is not None and 5

    def can_complete_oauth2_client_credentials(self, scopes: list[str]) -> t.Literal[False] | int:
        # There is an extra roundtrip for aquiring the token.
        # Should be cheap afterwards.
        return self.client_id is not None and 10

    def can_complete_mutualTLS(self) -> t.Literal[False] | int:
        # No extra cost, the tls setup will be done anyway.
        return self.cert is not None and 0

    async def http_basic_credentials(self) -> tuple[bytes, bytes]:
        assert self.username is not None
        assert self.password is not None
        return self.username, self.password

    async def api_key_credentials(self, security_scheme: oas.SecuritySchemeApiKey) -> str:
        if security_scheme.in_ == "cookie" and security_scheme.name in self._cookiejar:
            return self._cookiejar[security_scheme.name].value
        assert self.api_key is not None
        return self.api_key

    async def oauth2_client_credentials(self) -> tuple[bytes, bytes]:
        assert self.client_id is not None
        assert self.client_secret is not None
        return self.client_id, self.client_secret

    def tls_credentials(self) -> tuple[str, str | None]:
        assert self.cert is not None
        return (self.cert, self.key)
