import json

import httpx
import pytest
from fastapi import FastAPI

from app.api.mini_program import get_mini_program_nce_client, router
from app.services.mini_program import MiniProgramNCEClient


def _build_client(handler) -> MiniProgramNCEClient:
    return MiniProgramNCEClient(
        guest_service_url="https://nce.test/secoWS/service/NewGuestManagerServices",
        portal_auth_url="https://nce.test/PortalServer/AppPortalAuth",
        timeout_ms=1000,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_soap_guest_request_and_response_are_forwarded_without_json_wrapping() -> None:
    soap_body = b"<soapenv:Envelope><account>13800000000</account></soapenv:Envelope>"
    soap_response = b"<soapenv:Envelope><addGuestAccountResponse/></soapenv:Envelope>"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/secoWS/service/NewGuestManagerServices"
        assert request.headers["Content-Type"] == "application/soap+xml; charset=utf-8"
        assert request.headers["SOAPAction"] == "addGuestAccount"
        assert await request.aread() == soap_body
        return httpx.Response(200, content=soap_response, headers={"Content-Type": "application/soap+xml"})

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_mini_program_nce_client] = lambda: _build_client(handler)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/secoWS/service/NewGuestManagerServices",
            content=soap_body,
            headers={"Content-Type": "application/soap+xml; charset=utf-8", "SOAPAction": "addGuestAccount"},
        )

    assert response.status_code == 200
    assert response.content == soap_response
    assert response.headers["Content-Type"] == "application/soap+xml"


@pytest.mark.asyncio
async def test_upstream_error_status_body_and_content_type_are_preserved() -> None:
    upstream_body = b"<soapenv:Fault><faultcode>Client</faultcode></soapenv:Fault>"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=upstream_body, headers={"Content-Type": "application/soap+xml; charset=utf-8"})

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_mini_program_nce_client] = lambda: _build_client(handler)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/secoWS/service/NewGuestManagerServices", content=b"<request/>")

    assert response.status_code == 500
    assert response.content == upstream_body
    assert response.headers["Content-Type"] == "application/soap+xml; charset=utf-8"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("params", "upstream_payload"),
    [
        (
            {"messageType": "authRequest", "userName": "13800138000", "password": "13800138000"},
            {"resultCode": 0, "statusCode": 200, "sessionId": "session-001"},
        ),
        (
            {"messageType": "syncPortalAuthResultRequest", "sessionId": "session-001"},
            {"resultCode": 0, "portalAuthStatus": 1},
        ),
    ],
)
async def test_portal_auth_operations_preserve_query_and_response(params: dict[str, str], upstream_payload: dict) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/PortalServer/AppPortalAuth"
        assert dict(request.url.params) == params
        return httpx.Response(200, content=json.dumps(upstream_payload).encode(), headers={"Content-Type": "application/json"})

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_mini_program_nce_client] = lambda: _build_client(handler)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/PortalServer/AppPortalAuth", params=params)

    assert response.status_code == 200
    assert response.json() == upstream_payload


@pytest.mark.asyncio
async def test_portal_auth_preserves_repeated_query_parameters() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.multi_items() == [
            ("messageType", "authRequest"),
            ("extension", "first"),
            ("extension", "second"),
        ]
        return httpx.Response(200, json={"resultCode": 0})

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_mini_program_nce_client] = lambda: _build_client(handler)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/PortalServer/AppPortalAuth?messageType=authRequest&extension=first&extension=second"
        )

    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("upstream_exception", "expected_status", "expected_code"),
    [
        (httpx.ConnectError("connection refused"), 502, "MINI_PROGRAM_UPSTREAM_UNAVAILABLE"),
        (httpx.ReadTimeout("timed out"), 504, "MINI_PROGRAM_UPSTREAM_TIMEOUT"),
    ],
)
async def test_upstream_transport_failures_return_stable_gateway_errors(
    upstream_exception: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise upstream_exception

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_mini_program_nce_client] = lambda: _build_client(handler)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/PortalServer/AppPortalAuth", params={"messageType": "authRequest"})

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code


@pytest.mark.asyncio
async def test_soap_body_over_limit_is_rejected_before_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
    forwarded = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal forwarded
        forwarded = True
        return httpx.Response(200)

    monkeypatch.setattr("app.api.mini_program.settings.MINI_PROGRAM_MAX_SOAP_BODY_BYTES", 8)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_mini_program_nce_client] = lambda: _build_client(handler)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/secoWS/service/NewGuestManagerServices", content=b"123456789")

    assert response.status_code == 413
    assert forwarded is False


def test_openapi_exposes_legacy_soap_and_portal_contracts() -> None:
    app = FastAPI()
    app.include_router(router)
    schema = app.openapi()

    soap = schema["paths"]["/secoWS/service/NewGuestManagerServices"]["post"]
    portal = schema["paths"]["/PortalServer/AppPortalAuth"]["get"]
    assert "application/soap+xml" in soap["requestBody"]["content"]
    assert {parameter["name"] for parameter in portal["parameters"]} == {
        "messageType",
        "userName",
        "password",
        "sessionId",
    }
