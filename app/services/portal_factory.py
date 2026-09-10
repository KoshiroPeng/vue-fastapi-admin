from fastapi import Depends

from app.services.auth_transaction import AuthTransactionStore, get_auth_transaction_store
from app.services.boarding_pass import BoardingPassAuthenticationService, MockBoardingPassClient
from app.services.nce import NCEClient, get_nce_client
from app.services.passport import MockPassportOCRClient, PassportAuthenticationService
from app.services.wechat import WeChatAuthService
from app.settings import settings


def get_boarding_pass_service(
    nce: NCEClient = Depends(get_nce_client),
    store: AuthTransactionStore = Depends(get_auth_transaction_store),
) -> BoardingPassAuthenticationService:
    if not settings.BOARDING_PASS_MOCK_ENABLED:
        raise RuntimeError("真实登机牌验证客户端尚未配置")
    return BoardingPassAuthenticationService(
        verifier=MockBoardingPassClient(),
        nce=nce,
        store=store,
        pii_hash_secret=settings.PII_HASH_SECRET or "",
        transaction_ttl_seconds=settings.AUTH_TRANSACTION_TTL_SECONDS,
        guest_valid_minutes=settings.BOARDING_PASS_GUEST_VALID_MINUTES,
    )


def get_passport_service(
    nce: NCEClient = Depends(get_nce_client),
    store: AuthTransactionStore = Depends(get_auth_transaction_store),
) -> PassportAuthenticationService:
    if not settings.OCR_MOCK_ENABLED:
        raise RuntimeError("真实 OCR 客户端尚未配置")
    return PassportAuthenticationService(
        ocr=MockPassportOCRClient(),
        nce=nce,
        store=store,
        pii_hash_secret=settings.PII_HASH_SECRET or "",
        transaction_ttl_seconds=settings.AUTH_TRANSACTION_TTL_SECONDS,
        guest_valid_minutes=settings.PASSPORT_GUEST_VALID_MINUTES,
    )


def get_wechat_service(
    store: AuthTransactionStore = Depends(get_auth_transaction_store),
) -> WeChatAuthService:
    return WeChatAuthService(
        store=store,
        pii_hash_secret=settings.PII_HASH_SECRET or "",
        callback_secret=settings.WECHAT_CALLBACK_SECRET or "",
        transaction_ttl_seconds=settings.AUTH_TRANSACTION_TTL_SECONDS,
    )
