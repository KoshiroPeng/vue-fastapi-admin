from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class MiniProgramUpstreamResponse:
    status_code: int
    content: bytes
    content_type: str | None


class MiniProgramUpstreamError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class MiniProgramNCEClient:
    """Forward the legacy mini-program contract without reusing JSON guest adapters."""

    def __init__(
        self,
        *,
        guest_service_url: str,
        portal_auth_url: str,
        timeout_ms: int,
        verify_tls: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not guest_service_url or not portal_auth_url:
            raise ValueError("小程序 NCE 上游地址尚未配置")
        if timeout_ms <= 0:
            raise ValueError("小程序 NCE 请求超时必须大于 0")
        self._guest_service_url = guest_service_url
        self._portal_auth_url = portal_auth_url
        self._timeout = timeout_ms / 1000
        self._verify_tls = verify_tls
        self._transport = transport

    async def add_guest(self, body: bytes, content_type: str, soap_action: str | None = None) -> MiniProgramUpstreamResponse:
        headers = {"Content-Type": content_type}
        if soap_action:
            headers["SOAPAction"] = soap_action
        return await self._request("POST", self._guest_service_url, content=body, headers=headers)

    async def portal_auth(self, query_params: list[tuple[str, str]]) -> MiniProgramUpstreamResponse:
        return await self._request("GET", self._portal_auth_url, params=query_params)

    async def _request(self, method: str, url: str, **kwargs) -> MiniProgramUpstreamResponse:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                verify=self._verify_tls,
                transport=self._transport,
                trust_env=False,
            ) as client:
                response = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise MiniProgramUpstreamError("MINI_PROGRAM_UPSTREAM_TIMEOUT", "小程序认证上游请求超时", 504) from exc
        except httpx.RequestError as exc:
            raise MiniProgramUpstreamError("MINI_PROGRAM_UPSTREAM_UNAVAILABLE", "小程序认证上游不可用", 502) from exc
        return MiniProgramUpstreamResponse(
            status_code=response.status_code,
            content=response.content,
            content_type=response.headers.get("Content-Type"),
        )
