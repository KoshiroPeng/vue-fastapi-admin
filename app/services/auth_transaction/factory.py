from app.core.redis import redis_manager

from .redis_store import RedisAuthTransactionStore
from .store import AuthTransactionStore


def get_auth_transaction_store() -> AuthTransactionStore:
    return RedisAuthTransactionStore(redis_manager.client)
