from functools import lru_cache

from app.log import logger
from app.settings import settings

from .client import NCEClient
from .mock import MockNCEClient, MockNCEScenario


@lru_cache(maxsize=1)
def get_nce_client() -> NCEClient:
    if settings.NCE_MOCK_ENABLED:
        logger.info("event=nce_client_selected mode=mock reason=no_real_nce_environment")
        return MockNCEClient(scenario=MockNCEScenario(settings.NCE_MOCK_SCENARIO))

    raise RuntimeError("真实 NCE 客户端尚未配置，请启用 NCE_MOCK_ENABLED 或完成真实客户端实现")
