import asyncio
from collections.abc import Awaitable, Callable

from .client import NCEAuthorizationResult, NCEAuthorizationStatus, NCEClient, NCETerminalAuthorizationRequest
from .errors import NCEBusinessError, NCETimeoutError


async def authorize_terminal_and_wait(
    client: NCEClient,
    request: NCETerminalAuthorizationRequest,
    *,
    poll_attempts: int,
    poll_interval_ms: int,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> NCEAuthorizationResult:
    if poll_attempts <= 0:
        raise ValueError("HACA 轮询次数必须大于 0")
    if poll_interval_ms < 0:
        raise ValueError("HACA 轮询间隔不能小于 0")

    submitted = await client.authorize_terminal(request)
    if submitted.status is NCEAuthorizationStatus.SUCCESS:
        return submitted
    if submitted.status is NCEAuthorizationStatus.FAILED:
        raise NCEBusinessError(submitted.result_code, "NCE HACA 授权失败")

    for attempt in range(poll_attempts):
        if attempt > 0 or poll_interval_ms > 0:
            await sleep(poll_interval_ms / 1000)
        result = await client.query_authorization_result(submitted.session_id, request.node_ip)
        if result.status is NCEAuthorizationStatus.SUCCESS:
            return result
        if result.status is NCEAuthorizationStatus.FAILED:
            raise NCEBusinessError(result.result_code, "NCE HACA 授权失败")
    raise NCETimeoutError("NCE HACA 授权结果查询超时")
