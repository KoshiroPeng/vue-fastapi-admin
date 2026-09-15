import asyncio
import base64
import hashlib
import hmac
import ipaddress
import string
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.request_context import get_request_id
from app.log import logger

from .client import (
    NCEAccessToken,
    NCEAuthorizationResult,
    NCEAuthorizationStatus,
    NCEGuest,
    NCEGuestCreateRequest,
    NCEHealth,
    NCEHealthStatus,
    NCERadiusLog,
    NCERadiusLogPage,
    NCERadiusLogQuery,
    NCETerminalAuthorizationRequest,
    NCEUser,
    NCEUserPage,
    NCEUserQuery,
)
from .errors import NCEAuthenticationError, NCEBusinessError, NCEProtocolError, NCETimeoutError, NCEUnavailableError
from .response_parser import (
    parse_authorization_result,
    parse_nce_datetime,
    require_mapping,
    require_string,
    require_success_envelope,
)


class HuaweiNCEHttpClient:
    """Huawei iMaster NCE-Campus northbound adapter with one process-wide HTTP pool."""

    TOKEN_PATH = "/controller/v2/tokens"
    GUEST_PATH = "/controller/campus/v2/accountservice/accessuser/guest"
    USERS_PATH = "/controller/campus/v2/accountservice/accessuser/users"
    RADIUS_PATH = "/controller/campus/v1/accountservice/user/radiuslog"
    HACA_AUTHORIZATION_PATH = "/controller/cloud/v2/northbound/accessuser/haca/authorization"
    HACA_RESULT_PATH = "/controller/cloud/v2/northbound/accessuser/haca/authorizationresult/{session_id}"
    HACA_CUT_USER_PATH = "/controller/cloud/v2/northbound/accessuser/haca/cutuser"

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: SecretStr,
        guest_user_group_id: str,
        credential_secret: SecretStr,
        timeout: httpx.Timeout,
        limits: httpx.Limits,
        verify: bool | str = True,
        token_refresh_skew_seconds: int = 60,
        haca_status_field: str = "status",
        haca_success_values: set[str] | None = None,
        haca_pending_values: set[str] | None = None,
        haca_failure_values: set[str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not all((base_url, username, guest_user_group_id)):
            raise ValueError("NCE地址、账号和访客用户组不能为空")
        self._username = username
        self._password = password
        self._guest_user_group_id = guest_user_group_id
        self._credential_secret = credential_secret
        self._token_refresh_skew = timedelta(seconds=token_refresh_skew_seconds)
        self._haca_status_field = haca_status_field
        self._haca_success_values = self._normalized_values(haca_success_values or {"success", "true", "1"})
        self._haca_pending_values = self._normalized_values(haca_pending_values or {"pending", "processing", "0", "false"})
        self._haca_failure_values = self._normalized_values(
            haca_failure_values or {"failed", "failure", "error", "deny", "denied", "rejected", "-1"}
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._token: NCEAccessToken | None = None
        self._token_lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            limits=limits,
            verify=verify,
            transport=transport,
            trust_env=False,
            headers={"Accept": "application/json", "Accept-Language": "zh-CN"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> NCEHealth:
        started = time.perf_counter()
        try:
            await self.get_access_token()
        except (NCEAuthenticationError, NCEBusinessError, NCEProtocolError) as exc:
            status = NCEHealthStatus.DEGRADED
            message = "NCE 服务可达但鉴权或协议异常"
            logger.warning("event=nce_health_degraded request_id={} error_code={}", get_request_id() or "-", exc.code)
        except (NCETimeoutError, NCEUnavailableError) as exc:
            status = NCEHealthStatus.DOWN
            message = "NCE 服务不可用"
            logger.warning("event=nce_health_down request_id={} error_code={}", get_request_id() or "-", exc.code)
        else:
            status = NCEHealthStatus.HEALTHY
            message = "NCE 服务可用"
        latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        return NCEHealth(status=status, mode="real", configured=True, latency_ms=latency_ms, message=message)

    async def get_access_token(self) -> NCEAccessToken:
        token = self._token
        if self._token_is_usable(token):
            return token
        async with self._token_lock:
            token = self._token
            if self._token_is_usable(token):
                return token
            self._token = await self._fetch_access_token()
            return self._token

    async def create_guest(self, request: NCEGuestCreateRequest) -> NCEGuest:
        username = self._guest_username(request)
        password = self._guest_password(request.request_id)
        valid_until = self._clock() + timedelta(minutes=request.valid_duration_minutes)
        body: dict[str, Any] = {
            "userType": 20,
            "userName": username,
            "password": password,
            "userGroupId": self._guest_user_group_id,
            "effectiveType": 0,
            "validPeriodLong": int(valid_until.timestamp() * 1000),
            "maxAccessNum": str(request.max_devices),
            "accessType": "deny",
            "nextUpdateUserpass": False,
            "description": request.description,
        }
        if request.terminal_mac:
            body["bindInfo"] = {"bindMac": request.terminal_mac}
        payload = await self._request_json("POST", self.GUEST_PATH, json=body, expected_statuses={201})
        envelope = require_success_envelope(payload, "创建访客")
        data = require_mapping(envelope.get("data"), "创建访客")
        returned_username = require_string(data, "userName", "创建访客")
        if returned_username != username:
            raise NCEProtocolError("NCE创建访客返回了不一致的用户名")
        return NCEGuest(
            username=username,
            password=SecretStr(password),
            valid_until=valid_until,
            max_devices=request.max_devices,
        )

    async def authorize_terminal(self, request: NCETerminalAuthorizationRequest) -> NCEAuthorizationResult:
        address = ipaddress.ip_address(request.client_ip)
        body: dict[str, Any] = {
            "ssid": base64.b64encode(request.ssid.encode("utf-8")).decode("ascii"),
            "terminalMac": request.client_mac,
            "userName": request.username,
            "thirdAuthType": request.third_auth_type,
        }
        body["terminalIpV4" if address.version == 4 else "terminalIpV6"] = str(address)
        optional = {
            "deviceMac": request.device_mac,
            "deviceEsn": request.device_esn,
            "apMac": request.ap_mac,
            "nodeIp": request.node_ip,
            "policyName": request.policy_name,
            "temPermitTime": request.permit_seconds,
        }
        body.update({key: value for key, value in optional.items() if value is not None})
        payload = await self._request_json(
            "POST",
            self.HACA_AUTHORIZATION_PATH,
            json=body,
            expected_statuses={200},
        )
        envelope = require_success_envelope(payload, "HACA授权")
        session_id = require_string(envelope, "psessionid", "HACA授权")
        return NCEAuthorizationResult(
            session_id=session_id,
            status=NCEAuthorizationStatus.PENDING,
            result_code="0",
        )

    async def query_authorization_result(
        self,
        session_id: str,
        node_ip: str | None = None,
    ) -> NCEAuthorizationResult:
        payload = await self._request_json(
            "GET",
            self.HACA_RESULT_PATH.format(session_id=session_id),
            params={"nodeIp": node_ip} if node_ip else None,
            expected_statuses={200},
            retry_transient=True,
        )
        result = parse_authorization_result(
            payload,
            status_field=self._haca_status_field,
            success_values=self._haca_success_values,
            pending_values=self._haca_pending_values,
            failure_values=self._haca_failure_values,
        )
        if result.session_id != session_id:
            raise NCEProtocolError("NCE HACA查询返回了不一致的会话ID")
        return result

    async def disconnect_terminal(self, request: NCETerminalAuthorizationRequest, session_id: str) -> None:
        user_info: dict[str, Any] = {
            "terminalMac": request.client_mac,
            "userName": request.username,
            "psessionid": session_id,
        }
        address = ipaddress.ip_address(request.client_ip)
        user_info["terminalIpV4" if address.version == 4 else "terminalIpV6"] = str(address)
        optional = {"deviceMac": request.device_mac, "deviceEsn": request.device_esn, "nodeIp": request.node_ip}
        user_info.update({key: value for key, value in optional.items() if value is not None})
        payload = await self._request_json(
            "POST",
            self.HACA_CUT_USER_PATH,
            json={"thirdUserInfos": [user_info]},
            expected_statuses={200},
        )
        envelope = require_success_envelope(payload, "HACA强制下线")
        failures = envelope.get("failure")
        if isinstance(failures, list) and failures:
            raise NCEBusinessError("CUT_USER_FAILED", "NCE HACA强制下线失败")

    async def query_users(self, query: NCEUserQuery) -> NCEUserPage:
        params: dict[str, Any] = {"pageIndex": query.page, "pageSize": query.page_size}
        if query.user_name:
            params["userName"] = query.user_name
        if query.user_group_id:
            params["userGroupId"] = query.user_group_id
        payload = await self._request_json(
            "GET", self.USERS_PATH, params=params, expected_statuses={200}, retry_transient=True
        )
        envelope = require_success_envelope(payload, "查询用户")
        raw_data = envelope.get("data", [])
        if isinstance(raw_data, Mapping):
            raw_items = raw_data.get("data") or raw_data.get("items") or raw_data.get("users") or []
            total = raw_data.get("totalSize", raw_data.get("total", len(raw_items) if isinstance(raw_items, list) else 0))
        else:
            raw_items = raw_data
            total = envelope.get("totalSize", len(raw_items) if isinstance(raw_items, list) else 0)
        if not isinstance(raw_items, list):
            raise NCEProtocolError("NCE查询用户响应列表无效")
        items = [self._parse_user(item) for item in raw_items]
        if query.online_only:
            items = [item for item in items if item.is_online]
            total = len(items)
        return NCEUserPage(items=items, total=int(total), page=query.page, page_size=query.page_size)

    async def query_radius_logs(self, query: NCERadiusLogQuery) -> NCERadiusLogPage:
        result_code = {"success": 0, "failure": 1, "all": -1}[query.auth_result]
        body: dict[str, Any] = {
            "logType": "authen",
            "siteId": query.site_id,
            "queryMode": "ONE_SITE",
            "authenResultCode": result_code,
            "failReasonCode": query.fail_reason_code or 0,
            "authenStartTime": int(query.start_time.timestamp() * 1000),
            "authenEndTime": int(query.end_time.timestamp() * 1000),
            "userTypeCode": query.user_type_code if query.user_type_code is not None else -1,
            "authenTypeCode": query.auth_type_code if query.auth_type_code is not None else -1,
            "pageSize": query.page_size,
            "pageIndex": 1,
            "startRowKey": query.cursor or "",
        }
        if query.user_name:
            body["userName"] = query.user_name
        if query.terminal_ip:
            body["terminalIp"] = query.terminal_ip
        if query.terminal_mac:
            body["terminalMac"] = query.terminal_mac
        payload = await self._request_json(
            "POST", self.RADIUS_PATH, json=body, expected_statuses={200}, retry_transient=True
        )
        envelope = require_success_envelope(payload, "查询RADIUS日志")
        raw_items = envelope.get("data", [])
        if not isinstance(raw_items, list):
            raise NCEProtocolError("NCE RADIUS日志响应列表无效")
        items = [self._parse_radius_log(item) for item in raw_items]
        end_row_key = envelope.get("endRowKey")
        next_cursor = str(end_row_key) if end_row_key and len(items) >= query.page_size else None
        return NCERadiusLogPage(items=items, next_cursor=next_cursor, page_size=query.page_size)

    async def _fetch_access_token(self) -> NCEAccessToken:
        payload = await self._send_json(
            "POST",
            self.TOKEN_PATH,
            json={"userName": self._username, "password": self._password.get_secret_value()},
            expected_statuses={200},
            authenticated=False,
            retry_transient=True,
        )
        envelope = require_success_envelope(payload, "获取Token")
        data = require_mapping(envelope.get("data"), "获取Token")
        value = require_string(data, "token_id", "获取Token")
        expires_at = parse_nce_datetime(data.get("expiredDate"), "Token过期时间")
        return NCEAccessToken(value=SecretStr(value), expires_at=expires_at)

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        expected_statuses: set[int],
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        retry_transient: bool = False,
    ) -> Any:
        token = await self.get_access_token()
        headers = {"X-ACCESS-TOKEN": token.value.get_secret_value()}
        response = await self._send(
            method, path, params=params, json=json, headers=headers, retry_transient=retry_transient
        )
        if response.status_code in {401, 403}:
            await self._invalidate_token_if_current(token)
            refreshed = await self.get_access_token()
            headers["X-ACCESS-TOKEN"] = refreshed.value.get_secret_value()
            response = await self._send(method, path, params=params, json=json, headers=headers, retry_transient=False)
        return self._decode_response(response, expected_statuses, authenticated=True)

    async def _send_json(
        self,
        method: str,
        path: str,
        *,
        expected_statuses: set[int],
        authenticated: bool,
        json: Mapping[str, Any],
        retry_transient: bool,
    ) -> Any:
        response = await self._send(method, path, json=json, retry_transient=retry_transient)
        return self._decode_response(response, expected_statuses, authenticated=authenticated)

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        retry_transient: bool = False,
    ) -> httpx.Response:
        attempts = 2 if retry_transient else 1
        for attempt in range(attempts):
            started = time.perf_counter()
            try:
                response = await self._client.request(method, path, params=params, json=json, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.05)
                    continue
                raise NCETimeoutError("NCE请求超时") from exc
            except httpx.RequestError as exc:
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.05)
                    continue
                raise NCEUnavailableError("NCE服务不可用") from exc
            latency_ms = max(0, int((time.perf_counter() - started) * 1000))
            logger.info(
                "event=nce_http_call request_id={} method={} path={} status_code={} latency_ms={}",
                get_request_id() or "-",
                method,
                path,
                response.status_code,
                latency_ms,
            )
            if response.status_code >= 500 and attempt + 1 < attempts:
                await asyncio.sleep(0.05)
                continue
            return response
        raise NCEUnavailableError("NCE服务不可用")

    @staticmethod
    def _decode_response(response: httpx.Response, expected_statuses: set[int], *, authenticated: bool) -> Any:
        if response.status_code in {401, 403}:
            raise NCEAuthenticationError("NCE鉴权失败")
        if response.status_code >= 500:
            raise NCEUnavailableError("NCE服务端异常")
        try:
            payload = response.json()
        except ValueError as exc:
            raise NCEProtocolError("NCE响应不是有效JSON") from exc
        if response.status_code not in expected_statuses:
            result_code = str(payload.get("errcode", response.status_code)) if isinstance(payload, Mapping) else str(response.status_code)
            if not authenticated and response.status_code in {400, 405, 425, 460}:
                raise NCEAuthenticationError("NCE鉴权失败")
            raise NCEBusinessError(result_code, "NCE请求未成功")
        return payload

    async def _invalidate_token_if_current(self, failed_token: NCEAccessToken) -> None:
        async with self._token_lock:
            if self._token and self._token.value.get_secret_value() == failed_token.value.get_secret_value():
                self._token = None

    def _token_is_usable(self, token: NCEAccessToken | None) -> bool:
        if token is None:
            return False
        now = self._clock()
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return expires_at - self._token_refresh_skew > now

    @staticmethod
    def _normalized_values(values: set[str]) -> set[str]:
        return {str(value).strip().casefold() for value in values}

    @staticmethod
    def _guest_username(request: NCEGuestCreateRequest) -> str:
        digest = hashlib.sha256(request.request_id.encode("utf-8")).hexdigest()[:12]
        return f"{request.username_prefix}_{digest}"

    def _guest_password(self, request_id: str) -> str:
        digest = hmac.new(
            self._credential_secret.get_secret_value().encode("utf-8"),
            f"nce-guest:{request_id}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
        alphabet = string.ascii_letters + string.digits
        suffix = "".join(alphabet[byte % len(alphabet)] for byte in digest[:8])
        return f"Aa1!{suffix}"

    @staticmethod
    def _parse_user(raw: Any) -> NCEUser:
        item = require_mapping(raw, "用户记录")
        online_value = item.get("isOnline", item.get("online", item.get("status", False)))
        online = online_value is True or str(online_value).strip().casefold() in {"true", "1", "online"}
        connected = item.get("connectedAt", item.get("onlineTime"))
        return NCEUser(
            id=str(item.get("id") or item.get("userId") or ""),
            user_name=str(item.get("userName") or ""),
            user_group_id=str(item.get("userGroupId") or ""),
            user_group_name=str(item.get("userGroupName") or ""),
            user_type_code=int(item.get("userTypeCode", item.get("userType", 0))),
            is_online=online,
            terminal_ip=item.get("terminalIp") or item.get("terminalIpV4") or item.get("terminalIpV6"),
            terminal_mac=item.get("terminalMac"),
            access_ssid=item.get("accessSsid") or item.get("ssid"),
            connected_at=parse_nce_datetime(connected, "用户上线时间") if connected is not None else None,
        )

    @staticmethod
    def _parse_radius_log(raw: Any) -> NCERadiusLog:
        item = require_mapping(raw, "RADIUS日志记录")
        return NCERadiusLog(
            id=str(item.get("id") or ""),
            user_name=str(item.get("userName") or ""),
            user_group_name=str(item.get("userGroupName") or ""),
            user_type_code=int(item.get("userTypeCode", 0)),
            terminal_ip=str(item.get("terminalIpV4") or item.get("terminalIpV6") or item.get("terminalIp") or ""),
            terminal_mac=str(item.get("terminalMac") or ""),
            auth_type_code=int(item.get("authenTypeCode", item.get("authTypeCode", 0))),
            access_ssid=str(item.get("accessSsid") or item.get("ssid") or ""),
            authenticated_at=parse_nce_datetime(item.get("authenTime"), "RADIUS认证时间"),
            auth_result_code=int(item.get("authenResultCode", item.get("authResultCode", 0))),
            fail_reason_code=int(item.get("failReasonCode", 0)),
        )
