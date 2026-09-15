from functools import lru_cache

import httpx
from pydantic import SecretStr

from app.log import logger
from app.settings import settings

from .client import NCEClient
from .http_client import HuaweiNCEHttpClient
from .mock import MockNCEClient, MockNCEScenario


@lru_cache(maxsize=1)
def get_nce_client() -> NCEClient:
    if settings.NCE_MOCK_ENABLED:
        logger.info("event=nce_client_selected mode=mock reason=no_real_nce_environment")
        return MockNCEClient(scenario=MockNCEScenario(settings.NCE_MOCK_SCENARIO))

    missing = [
        name
        for name, value in {
            "NCE_BASE_URL": settings.NCE_BASE_URL,
            "NCE_USERNAME": settings.NCE_USERNAME,
            "NCE_PASSWORD": settings.NCE_PASSWORD,
            "NCE_GUEST_USER_GROUP_ID": settings.NCE_GUEST_USER_GROUP_ID,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"真实 NCE 客户端缺少配置：{', '.join(missing)}")
    verify: bool | str = settings.NCE_CA_FILE or settings.NCE_TLS_VERIFY
    logger.info("event=nce_client_selected mode=real")
    return HuaweiNCEHttpClient(
        base_url=settings.NCE_BASE_URL or "",
        username=settings.NCE_USERNAME or "",
        password=settings.NCE_PASSWORD or SecretStr(""),
        guest_user_group_id=settings.NCE_GUEST_USER_GROUP_ID or "",
        credential_secret=SecretStr(settings.SECRET_KEY),
        timeout=httpx.Timeout(
            connect=settings.NCE_CONNECT_TIMEOUT_SECONDS,
            read=settings.NCE_READ_TIMEOUT_SECONDS,
            write=settings.NCE_WRITE_TIMEOUT_SECONDS,
            pool=settings.NCE_POOL_TIMEOUT_SECONDS,
        ),
        limits=httpx.Limits(
            max_connections=settings.NCE_MAX_CONNECTIONS,
            max_keepalive_connections=settings.NCE_MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=30,
        ),
        verify=verify,
        token_refresh_skew_seconds=settings.NCE_TOKEN_REFRESH_SKEW_SECONDS,
        haca_status_field=settings.NCE_HACA_STATUS_FIELD,
        haca_success_values=set(settings.NCE_HACA_SUCCESS_VALUES),
        haca_pending_values=set(settings.NCE_HACA_PENDING_VALUES),
        haca_failure_values=set(settings.NCE_HACA_FAILURE_VALUES),
    )


async def close_nce_client() -> None:
    if get_nce_client.cache_info().currsize == 0:
        return
    client = get_nce_client()
    close = getattr(client, "aclose", None)
    if close is not None:
        await close()
    get_nce_client.cache_clear()
