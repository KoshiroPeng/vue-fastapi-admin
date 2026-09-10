from .models import AuthStatus


class AuthTransactionError(Exception):
    """Base error for short-lived authentication transaction operations."""


class AuthTransactionNotFound(AuthTransactionError):
    pass


class InvalidAuthStatusTransition(AuthTransactionError):
    def __init__(self, current: AuthStatus, target: AuthStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"invalid authentication status transition: {current.value} -> {target.value}")


class AuthTransactionAlreadyConsumed(AuthTransactionError):
    pass


class AuthTransactionNotConsumable(AuthTransactionError):
    pass
