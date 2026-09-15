from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.core.request_context import get_request_id
from app.services.mini_program import MiniProgramNCEClient, MiniProgramUpstreamError, MiniProgramUpstreamResponse
from app.settings import settings

router = APIRouter(tags=["第三方小程序兼容接口"])

_SOAP_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "application/soap+xml": {
                "schema": {"type": "string"},
                "example": "<soapenv:Envelope>...</soapenv:Envelope>",
            }
        },
    }
}

_PORTAL_AUTH_PARAMETERS = [
    {
        "name": "messageType",
        "in": "query",
        "required": True,
        "schema": {"type": "string", "enum": ["authRequest", "syncPortalAuthResultRequest"]},
        "description": "authRequest 表示发起认证；syncPortalAuthResultRequest 表示同步认证结果。",
    },
    {"name": "userName", "in": "query", "required": False, "schema": {"type": "string"}},
    {"name": "password", "in": "query", "required": False, "schema": {"type": "string", "format": "password"}},
    {"name": "sessionId", "in": "query", "required": False, "schema": {"type": "string"}},
]


@lru_cache(maxsize=1)
def get_mini_program_nce_client() -> MiniProgramNCEClient:
    if not settings.MINI_PROGRAM_GUEST_SERVICE_URL or not settings.MINI_PROGRAM_PORTAL_AUTH_URL:
        raise HTTPException(status_code=503, detail="小程序 NCE 上游地址尚未配置")
    return MiniProgramNCEClient(
        guest_service_url=settings.MINI_PROGRAM_GUEST_SERVICE_URL,
        portal_auth_url=settings.MINI_PROGRAM_PORTAL_AUTH_URL,
        timeout_ms=settings.MINI_PROGRAM_TIMEOUT_MS,
        verify_tls=settings.MINI_PROGRAM_TLS_VERIFY,
    )


async def _read_limited_body(request: Request) -> bytes:
    content_length = request.headers.get("Content-Length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Content-Length 无效") from exc
        if declared_size < 0 or declared_size > settings.MINI_PROGRAM_MAX_SOAP_BODY_BYTES:
            raise HTTPException(status_code=413, detail="SOAP 请求体超过大小限制")

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > settings.MINI_PROGRAM_MAX_SOAP_BODY_BYTES:
            body.clear()
            raise HTTPException(status_code=413, detail="SOAP 请求体超过大小限制")
    return bytes(body)


def _passthrough_response(upstream: MiniProgramUpstreamResponse) -> Response:
    headers = {"Content-Type": upstream.content_type} if upstream.content_type else None
    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)


def _upstream_error_response(exc: MiniProgramUpstreamError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": str(exc),
                "requestId": get_request_id() or "-",
            }
        },
    )


@router.post(
    "/secoWS/service/NewGuestManagerServices",
    summary="小程序添加访客 SOAP WebService 兼容代理",
    response_class=Response,
    openapi_extra=_SOAP_OPENAPI,
    responses={200: {"content": {"application/soap+xml": {"schema": {"type": "string"}}}}},
)
async def add_guest_account(
    request: Request,
    client: MiniProgramNCEClient = Depends(get_mini_program_nce_client),
) -> Response:
    body = await _read_limited_body(request)
    try:
        upstream = await client.add_guest(
            body,
            request.headers.get("Content-Type", "application/soap+xml"),
            request.headers.get("SOAPAction"),
        )
    except MiniProgramUpstreamError as exc:
        return _upstream_error_response(exc)
    return _passthrough_response(upstream)


@router.get(
    "/PortalServer/AppPortalAuth",
    summary="小程序 WiFi 认证及结果同步兼容代理",
    openapi_extra={"parameters": _PORTAL_AUTH_PARAMETERS},
    responses={
        200: {
            "content": {
                "application/json": {
                    "schema": {
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "resultCode": {"type": "integer"},
                                    "statusCode": {"type": "integer"},
                                    "sessionId": {"type": "string"},
                                },
                            },
                            {
                                "type": "object",
                                "properties": {
                                    "resultCode": {"type": "integer"},
                                    "portalAuthStatus": {"type": "integer"},
                                },
                            },
                        ]
                    }
                }
            }
        }
    },
)
async def app_portal_auth(
    request: Request,
    client: MiniProgramNCEClient = Depends(get_mini_program_nce_client),
) -> Response:
    try:
        upstream = await client.portal_auth(list(request.query_params.multi_items()))
    except MiniProgramUpstreamError as exc:
        return _upstream_error_response(exc)
    return _passthrough_response(upstream)
