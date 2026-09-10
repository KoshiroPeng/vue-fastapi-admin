import httpx
import pytest
from fastapi import FastAPI
from fastapi.middleware import Middleware

from app.core.request_context import RequestContextMiddleware, get_request_id


@pytest.mark.asyncio
async def test_request_id_is_propagated_to_context_and_response() -> None:
    app = FastAPI(middleware=[Middleware(RequestContextMiddleware)])

    @app.get("/trace")
    async def trace() -> dict[str, str]:
        return {"request_id": get_request_id()}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/trace", headers={"X-Request-ID": "request-abc-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-abc-123"
    assert response.json()["request_id"] == "request-abc-123"


@pytest.mark.asyncio
async def test_invalid_request_id_is_replaced() -> None:
    app = FastAPI(middleware=[Middleware(RequestContextMiddleware)])

    @app.get("/trace")
    async def trace() -> dict[str, str]:
        return {"request_id": get_request_id()}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/trace", headers={"X-Request-ID": "contains spaces!"})

    request_id = response.headers["X-Request-ID"]
    assert request_id != "contains spaces!"
    assert len(request_id) == 32
