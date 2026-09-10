class NCEError(Exception):
    """Base error raised by every NCE adapter implementation."""

    code = "NCE_ERROR"


class NCEAuthenticationError(NCEError):
    code = "NCE_AUTHENTICATION_FAILED"


class NCEBusinessError(NCEError):
    code = "NCE_BUSINESS_ERROR"

    def __init__(self, result_code: str, message: str = "NCE 业务请求失败") -> None:
        self.result_code = result_code
        super().__init__(message)


class NCETimeoutError(NCEError):
    code = "NCE_TIMEOUT"


class NCEUnavailableError(NCEError):
    code = "NCE_UNAVAILABLE"
