class RiskControlError(Exception):
    """Expected security decision with stable, public HTTP semantics."""

    status_code = 400
    error_code = "RISK_CONTROL_REJECTED"
    public_message = "请求已被安全策略拒绝"


class RequestExpired(RiskControlError):
    status_code = 401
    error_code = "REQUEST_EXPIRED"
    public_message = "请求已过期，请重新操作"


class ReplayDetected(RiskControlError):
    status_code = 409
    error_code = "REPLAY_DETECTED"
    public_message = "请求已处理，请勿重复提交"


class RateLimitExceeded(RiskControlError):
    status_code = 429
    error_code = "RATE_LIMITED"
    public_message = "操作过于频繁，请稍后再试"

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"rate limit exceeded; retry after {retry_after_seconds} seconds")


class IdempotencyConflict(RiskControlError):
    status_code = 409
    error_code = "IDEMPOTENCY_CONFLICT"
    public_message = "请求正在处理或已经完成，请勿重复提交"
