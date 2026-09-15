# 深圳机场 WiFi 多方式认证系统接口文档

| 项目 | 内容 |
| :--- | :--- |
| 文档版本 | V2.0 |
| 编制日期 | 2026-09-15 |
| 适用系统 | 深圳机场 WiFi Portal、FastAPI 认证服务及相关第三方系统 |
| 阅读方式 | 按短信、登机牌、护照、微信小程序、取号机业务阅读 |

## 1. 总体说明

`portal/` 是正式旅客 Portal 前端，当前仍在开发。认证请求原则上由 Portal 调用本系统 FastAPI，再由 FastAPI 调用 NCE 或其他第三方系统。浏览器不得接触 NCE Token、临时访客密码或 HACA 会话 ID。

本文档中：

- **已实现**表示当前代码和自动化测试已存在，不代表已经通过现场真实系统联调。
- **待实现**表示目标流程已经明确，但当前 FastAPI 还没有对应路由或真实客户端。
- **待现场确认**表示缺少正式地址、字段、鉴权、状态值或测试数据，不能依据 Mock 推断生产行为。

### 1.1 业务与接口总览

| 业务 | Portal 调用 FastAPI | FastAPI 调用外部系统 | 当前状态 |
| :--- | :--- | :--- | :--- |
| 短信认证 | 获取验证码、提交手机号和验证码 | NCE 短信及 Portal 认证接口 | FastAPI 接口待实现；当前 Portal 仍直连 NCE `/portalauth/*` |
| 登机牌认证 | `POST /api/v1/portal/boarding-pass/verify` | 登机牌验证、NCE 创建访客、HACA 授权及结果查询 | FastAPI 编排已实现；登机牌真实客户端和 Portal 接入待完成 |
| 护照认证 | `POST /api/v1/portal/passport/verify` | OCR、NCE 创建访客、HACA 授权及结果查询 | FastAPI 编排已实现；OCR 真实客户端和 Portal 接入待完成 |
| 微信认证 | 创建事务、查询状态 | 小程序通过兼容接口调用 NCE，并向 FastAPI 回写结果 | FastAPI 已实现；正式 Portal、小程序和真实 NCE 待联调 |
| 取号机认证 | 旅客提交小票账号和密码 | NCE Portal 账号密码认证 | 取号机创建账号接口已实现；Portal 登录 FastAPI 接口待实现 |
| 管理运维 | 不属于旅客 Portal | NCE 用户、RADIUS、健康和统计接口 | 管理台接口已实现，不在本文档展开 |

### 1.2 Portal 终端上下文

Portal 从 NCE 跳转 URL 读取以下参数，并传给 FastAPI：

| Portal 参数 | FastAPI 字段 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `uaddress` / `wlanuserip` | `clientIp` 或 `X-Client-IP` | 是 | 旅客终端 IPv4 或 IPv6 |
| `umac` / `wlanusermac` | `clientMac` 或 `X-Client-MAC` | 是 | 旅客终端 MAC |
| `ssid` | `ssid` 或 `X-SSID` | 否 | 当前 SSID |
| `armac` / `accessMac` | `deviceMac` 或 `X-Device-MAC` | 条件必填 | 与 `deviceEsn` 至少提供一个 |
| `esn` | `deviceEsn` 或 `X-Device-ESN` | 条件必填 | 与 `deviceMac` 至少提供一个 |
| `apmac` | `apMac` 或 `X-AP-MAC` | 否 | AP MAC |
| `ac-ip` | `nodeIp` 或 `X-Node-IP` | 否 | 执行 HACA 授权的节点 IPv4 |

### 1.3 FastAPI 通用响应

成功响应：

```json
{
  "code": 200,
  "msg": "OK",
  "data": {}
}
```

失败响应：

```json
{
  "code": 400,
  "msg": "错误说明",
  "data": null,
  "error_code": "可选的稳定错误码"
}
```

| HTTP | 说明 |
| :--- | :--- |
| 400 | 业务校验未通过或入口上下文缺失 |
| 401 | 签名或认证失败 |
| 404 | 认证事务不存在、已过期或开发接口在生产禁用 |
| 409 | Nonce 重放或幂等冲突 |
| 413 | 图片或 SOAP 请求体过大 |
| 422 | 请求字段格式不符合契约 |
| 429 | IP 或 MAC 触发限流，响应带 `Retry-After` |
| 502 | NCE 或其他第三方返回失败、协议异常或不可用 |
| 504 | 外部系统调用超时 |

Portal 可发送 `X-Request-ID`，FastAPI 在响应 Header 返回最终请求 ID，便于日志排查。

## 2. 短信认证业务

### 2.1 目标流程

```text
Portal 输入手机号
→ Portal 调 FastAPI 获取短信验证码
→ FastAPI 调 NCE 短信接口
→ 旅客输入短信验证码
→ Portal 把手机号和验证码提交给 FastAPI
→ FastAPI 调 NCE Portal 认证接口并查询认证结果
→ FastAPI 明确确认放行后返回 networkAuthorized=true
```

当前 FastAPI 尚未实现以下两个接口。现有 `portal/sms` 仍通过华为 `auth.js` 直接调用 `/portalauth/getSmsPassword`、`/portalauth/login` 和 `/portalauth/syncPortalResult`，不符合新的统一后端调用目标。

### 2.2 获取短信验证码（待实现）

目标接口：`POST /api/v1/portal/sms/code`

```json
{
  "phone": "13800000000",
  "countryCode": "+86",
  "captcha": "ABCD",
  "clientIp": "10.85.73.8",
  "clientMac": "AA-BB-CC-DD-EE-FF",
  "ssid": "Airport-Free-WiFi",
  "deviceMac": "11-22-33-44-55-66",
  "deviceEsn": null,
  "apMac": "22-33-44-55-66-77",
  "nodeIp": "172.16.4.107"
}
```

成功响应不返回验证码：

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "sent": true,
    "retryAfterSeconds": 60
  }
}
```

FastAPI 上游调用目标为 NCE `/portalauth/getSmsPassword`。正式实现前需要现场确认验证码图片是否必需、`authType`、`pushPageId`、`lang`、`registerCode` 等字段，以及上游成功和错误响应。

### 2.3 手机号和验证码认证（待实现）

目标接口：`POST /api/v1/portal/sms/auth`

```json
{
  "phone": "13800000000",
  "countryCode": "+86",
  "smsCode": "123456",
  "clientIp": "10.85.73.8",
  "clientMac": "AA-BB-CC-DD-EE-FF",
  "ssid": "Airport-Free-WiFi",
  "deviceMac": "11-22-33-44-55-66",
  "deviceEsn": null,
  "apMac": "22-33-44-55-66-77",
  "nodeIp": "172.16.4.107"
}
```

FastAPI 调用 NCE `/portalauth/login`，并按现场契约调用 `/portalauth/syncPortalResult` 查询最终结果。只有 NCE 明确放行后才返回：

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "networkAuthorized": true
  }
}
```

获取验证码和认证均属于防刷敏感接口，应按手机号摘要、终端 IP 和 MAC 限流。验证码、手机号明文和 NCE 会话信息不得写入日志。

## 3. 登机牌认证业务

### 3.1 业务流程

```text
Portal 提交航班日期、航班号、座位号和证件后四位
→ FastAPI 调登机牌系统验证三要素
→ FastAPI 调 NCE 创建临时访客
→ FastAPI 提交 HACA 终端授权
→ FastAPI 轮询 HACA 授权结果
→ 明确成功后返回 networkAuthorized=true
```

### 3.2 Portal 调 FastAPI（已实现）

`POST /api/v1/portal/boarding-pass/verify`

```json
{
  "flightDate": "2026-09-10",
  "flightNo": "CA1234",
  "seatNo": "16A",
  "documentLast4": "5678",
  "clientIp": "10.85.73.8",
  "clientMac": "AA-BB-CC-DD-EE-FF",
  "ssid": "Airport-Free-WiFi",
  "deviceMac": "11-22-33-44-55-66",
  "deviceEsn": null,
  "apMac": "22-33-44-55-66-77",
  "nodeIp": "172.16.4.107"
}
```

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "verified": true,
    "networkAuthorized": true,
    "authTxId": "tx_3fe34d91c6924cbca3307f42f71d9501",
    "validUntil": "2026-09-10T18:30:00+08:00"
  }
}
```

该 POST 会创建访客并执行网络授权，Portal 超时后不得盲目自动重试。当前 `portal/boarding-pass` 中的 `boardingPassAuth()` 尚未实现，仍需接入本接口。

### 3.3 FastAPI 调登机牌系统（真实客户端待实现）

需求确认稿建议请求：

```json
{
  "requestId": "与本系统请求 ID 一致",
  "requestTime": "2026-09-10T10:30:00+08:00",
  "airportCode": "SZX",
  "flightDate": "2026-09-10",
  "flightNo": "CA1234",
  "seatNo": "16A",
  "documentLast4": "5678",
  "clientId": "SZX_WIFI_PORTAL"
}
```

预期成功响应：

```json
{
  "requestId": "与请求一致",
  "success": true,
  "verified": true,
  "code": "0000",
  "message": "Verified",
  "flightStatus": "BOARDING",
  "validUntil": "2026-09-10T18:30:00+08:00",
  "responseTime": "2026-09-10T10:30:00+08:00"
}
```

结果码基线：`0000` 成功；`1001` 验证失败；`1002` 不在范围；`1003` 登机牌无效或取消；`1004` 超出时间窗口；`2001` 格式错误；`2002` 鉴权失败；`3001` 数据源不可用；`3002` 超时。

正式 Base URL、mTLS/OAuth2 鉴权、证书或 Token 获取方式仍待第三方确认。

### 3.4 FastAPI 调 NCE 创建访客和 HACA

登机牌验证成功后依次调用：

1. `POST /controller/v2/tokens`：获取 `x-access-token`。
2. `POST /controller/campus/v2/accountservice/accessuser/guest`：创建单终端临时访客。
3. `POST /controller/cloud/v2/northbound/accessuser/haca/authorization`：提交终端授权，取得 `psessionid`。
4. `GET /controller/cloud/v2/northbound/accessuser/haca/authorizationresult/{psessionid}`：轮询授权结果。

提交 HACA 的主要字段包括 SSID Base64、终端 IPv4/IPv6、终端 MAC、临时用户名、`thirdAuthType=7`、接入设备 MAC/ESN、AP MAC、节点 IP、策略名和临时放行秒数。

提交成功只表示 NCE 已受理。只有结果查询明确命中成功值，FastAPI 才返回 `networkAuthorized=true`；未知状态按处理中处理，轮询用尽后返回超时。

## 4. 护照认证业务

### 4.1 业务流程

```text
Portal 拍摄护照资料页
→ Portal 将原始图像流上传 FastAPI
→ FastAPI 调 OCR 服务识别护照并校验 MRZ
→ FastAPI 调 NCE 创建临时访客
→ FastAPI 提交并轮询 HACA 授权
→ 明确成功后返回 networkAuthorized=true
```

### 4.2 Portal 调 FastAPI（已实现）

`POST /api/v1/portal/passport/verify`

| 内容 | 要求 |
| :--- | :--- |
| Body | 原始 JPG 或 PNG 二进制流，不使用 JSON 或 multipart |
| `Content-Type` | `image/jpeg` 或 `image/png` |
| `X-Client-IP`、`X-Client-MAC` | 必填 |
| `X-Device-MAC`、`X-Device-ESN` | 至少提供一个 |
| `X-SSID`、`X-AP-MAC`、`X-Node-IP` | 可选 |
| 大小限制 | 默认最大 4MB |

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "verified": true,
    "networkAuthorized": true,
    "authTxId": "tx_3fe34d91c6924cbca3307f42f71d9501",
    "passportNoMasked": "E****1234",
    "validUntil": "2026-09-10T18:30:00+08:00"
  }
}
```

护照图像只在内存中处理，不落盘，不写日志。当前 `portal/passport` 仍调用旧的 `onTakePhone()` 和 `onekeyLogin()`，需要改为上传图像流到本接口。

### 4.3 FastAPI 调 OCR（真实客户端待实现）

现有代码只定义了 OCR 客户端边界和 Mock。正式实现仍缺少 OCR Base URL、鉴权方式、文件上传字段、护照 `typeId`、成功字段、MRZ 字段和完整错误码。

OCR 成功且 MRZ 校验通过后，FastAPI 复用登机牌业务中的 NCE 创建访客和 HACA 授权流程。

## 5. 微信小程序认证业务

### 5.1 业务流程

```text
Portal 创建微信认证事务
→ Portal 打开第三方微信小程序
→ 小程序通过 FastAPI 兼容接口添加访客
→ 小程序通过 FastAPI 兼容接口发起 NCE Portal 认证
→ 小程序同步并确认 NCE Portal 认证结果
→ 小程序向 FastAPI 回写认证状态
→ Portal 轮询 FastAPI 状态并展示结果
```

### 5.2 Portal 创建认证事务（已实现）

`POST /api/v1/portal/wechat/auth/start`

```json
{
  "clientIp": "10.85.73.8",
  "clientMac": "AA-BB-CC-DD-EE-FF",
  "ssid": "Airport-Free-WiFi",
  "deviceMac": "11-22-33-44-55-66"
}
```

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "authTxId": "tx_3fe34d91c6924cbca3307f42f71d9501",
    "status": "PENDING",
    "expireAt": "2026-09-10T10:35:00+08:00"
  }
}
```

### 5.3 小程序添加访客（已实现兼容代理）

`POST /secoWS/service/NewGuestManagerServices`

小程序保持原有 SOAP WebService 契约，主要字段包括 `account`、`authPolicy`、`changePwdAtNextLogin`、`orgName`、`password`、`validBeginPeriod` 和 `validPeriod`。FastAPI 将 SOAP Body、`Content-Type` 和可选 `SOAPAction` 原样代理到 NCE，并原样返回 NCE HTTP 状态、Content-Type 和响应体。

### 5.4 小程序发起 NCE 认证（已实现兼容代理）

```http
GET /PortalServer/AppPortalAuth?messageType=authRequest&userName={userName}&password={password}
```

FastAPI 原样转发全部 Query 参数。成功响应以现场既有契约为准，当前基线包含 `resultCode`、`statusCode` 和 `sessionId`。

### 5.5 小程序同步认证结果（已实现兼容代理）

```http
GET /PortalServer/AppPortalAuth?messageType=syncPortalAuthResultRequest&sessionId={sessionId}
```

只有 `resultCode=0` 且 `portalAuthStatus=1` 才表示 NCE 已明确放行。小程序随后才能向 FastAPI 回写成功。

### 5.6 小程序回写 FastAPI（已实现，待真实联调）

`POST /api/v1/portal/wechat/auth/callback`

Header：`X-Wx-Timestamp`、`X-Wx-Nonce`、`X-Wx-Signature` 和 `Content-Type: application/json`。

```json
{
  "authTxId": "tx_3fe34d91c6924cbca3307f42f71d9501",
  "result": "SUCCESS",
  "nceSuccess": true
}
```

签名原文为 `timestamp + "\n" + nonce + "\n" + SHA256(rawBody)`，使用 `WECHAT_CALLBACK_SECRET` 计算 HMAC-SHA256。只有 `result=SUCCESS` 且 `nceSuccess=true` 时事务才更新为成功。

### 5.7 Portal 查询认证结果（已实现）

```http
GET /api/v1/portal/wechat/auth/status?auth_tx_id={authTxId}
```

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "authTxId": "tx_3fe34d91c6924cbca3307f42f71d9501",
    "status": "SUCCESS",
    "expireAt": "2026-09-10T10:35:00+08:00"
  }
}
```

Portal 建议每 2 秒查询一次，60 秒后停止。只在 `SUCCESS` 时展示联网成功；`PENDING` 继续等待，`FAILED` 提示重试，404 表示事务不存在或已过期。

`POST /api/v1/portal/wechat/auth/mock-complete?auth_tx_id=...` 只在 `DEBUG=true` 且 NCE Mock 开启时用于开发，生产返回 404。

## 6. 取号机认证业务

### 6.1 业务流程

```text
取号机扫描证件并调用 FastAPI 创建临时访客
→ 取号机打印账号和密码
→ 旅客在 Portal 输入小票账号和密码
→ Portal 调 FastAPI
→ FastAPI 调 NCE Portal 账号密码认证并查询结果
→ 明确成功后返回 networkAuthorized=true
```

### 6.2 取号机创建访客（已实现）

`POST /api/v1/kiosk/create-guest`

鉴权采用来源 IP 白名单、HMAC-SHA256、时间戳、Nonce 和幂等键。

| Header | 要求 |
| :--- | :--- |
| `X-Kiosk-Id` | 1 至 64 位取号机编号 |
| `X-Timestamp` | Unix 秒级时间戳，默认允许正负 300 秒 |
| `X-Nonce` | 8 至 128 字符，每次请求唯一 |
| `Idempotency-Key` | 8 至 128 字符，同一业务操作保持不变 |
| `X-Signature` | 64 位小写 HMAC-SHA256 十六进制字符串 |

```json
{
  "idType": "PASSPORT",
  "idDigest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

`idDigest` 必须是不可逆 SHA-256 摘要，不得传完整证件号。签名原文：

```text
POST
/api/v1/kiosk/create-guest
{X-Kiosk-Id}
{X-Timestamp}
{X-Nonce}
{Idempotency-Key}
{hex_lowercase(SHA256(rawBodyBytes))}
```

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "username": "kiosk_ab12cd34",
    "password": "一次性返回的临时密码",
    "validUntil": "2026-09-11T10:30:00+08:00",
    "maxDevices": 1
  }
}
```

### 6.3 Portal 使用小票登录（待实现）

目标接口：`POST /api/v1/portal/account/auth`

```json
{
  "username": "kiosk_ab12cd34",
  "password": "旅客输入的小票密码",
  "clientIp": "10.85.73.8",
  "clientMac": "AA-BB-CC-DD-EE-FF",
  "ssid": "Airport-Free-WiFi",
  "deviceMac": "11-22-33-44-55-66"
}
```

FastAPI 调 NCE `/portalauth/login` 并查询最终认证结果，明确放行后返回：

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "networkAuthorized": true
  }
}
```

当前 `portal/kiosk-account` 仍调用华为原生 `login()`，尚未经过 FastAPI。正式实现不得记录小票密码，也不得因超时自动重复提交登录。

## 7. 附录

### 7.1 管理运维接口

这些接口由 Vue 管理台使用，不属于旅客 Portal，也不提供给外部系统：

| 功能 | FastAPI 接口 |
| :--- | :--- |
| 外部服务健康 | `GET /api/v1/dashboard/health` |
| 认证统计 | `GET /api/v1/dashboard/statistics` |
| 在线用户 | `GET /api/v1/dashboard/online-users` |
| RADIUS 日志 | `POST /api/v1/dashboard/radius-logs` |
| 运行配置摘要 | `GET /api/v1/runtime-config/summary` |

管理接口要求管理员 JWT 和接口权限，不能由 Portal 匿名调用。

### 7.2 部署与安全要求

#### 7.2.1 Portal 调用地址

- 正式 Portal 由 NCE HTTPS 页面加载时，FastAPI 的 Nginx 入口也必须使用受信任的 HTTPS，不能从 HTTPS 页面请求 HTTP API。
- `CORS_ORIGINS` 必须精确加入浏览器地址栏中真实 Portal 页面的 Origin，不得使用 `*`。
- Nginx 必须允许 `OPTIONS` 预检；JSON 请求及护照接口自定义 Header 会触发预检。
- 如果 NCE 页面启用了 CSP，需要把 FastAPI HTTPS 地址加入 `connect-src`。
- Portal 统一从构建或部署配置读取一个 FastAPI Base URL，不在各认证页面分别硬编码。

#### 7.2.2 敏感信息

禁止写入日志、数据库、Redis 长期数据、工单或普通聊天工具：

- 手机号、短信验证码和小票密码；
- NCE `x-access-token`、Cookie、XSRF Token、临时访客密码和 HACA `psessionid`；
- 护照原图、完整护照号、证件后四位和 OCR 原始报文；
- 生产 HMAC 密钥、OAuth Client Secret、私钥。

#### 7.2.3 重试原则

- Token 获取失败可以按客户端策略重试；401/403 只允许刷新 Token 后重放一次。
- 用户、在线状态和 RADIUS 等只读查询可对瞬时网络错误有限重试。
- 创建访客、短信发送、登录、HACA 授权和强制下线发生超时时不得盲目自动重试，必须先查询状态或依赖幂等机制。

### 7.3 当前开发缺口

| 优先级 | 缺口 | 完成标准 |
| :--- | :--- | :--- |
| P0 | FastAPI 短信获取验证码接口 | Portal 不再直接调用 `/portalauth/getSmsPassword`，验证码发送正向、限流和失败用例通过 |
| P0 | FastAPI 短信认证及结果查询接口 | 手机号和验证码由 FastAPI 提交 NCE，只有明确放行才返回成功 |
| P0 | FastAPI 小票账号登录接口 | `portal/kiosk-account` 不再直接调用 NCE 登录接口 |
| P0 | 正式 Portal 接入现有登机牌、护照和微信接口 | `portal/` 页面真实发出请求，成功、失败、超时和 429 均正确展示 |
| P0 | 登机牌真实客户端 | 正式 URL、鉴权、证书、结果码和脱敏测试数据全部联调通过 |
| P0 | OCR 真实客户端 | 正式 URL、鉴权、上传字段、`typeId`、响应字段和错误码全部联调通过 |
| P0 | 现场 HACA 契约 | 状态字段和值域、策略名、`thirdAuthType`、节点参数和接口权限确认 |
| P1 | Portal HTTPS、CORS、CSP 联调 | iOS、Android 和微信浏览器均能从 NCE 页面访问 FastAPI |
| P1 | 双实例性能及故障切换 | 50 RPS 认证压测、单实例退出和恢复演练通过 |

### 7.4 契约优先级

发生冲突时按以下顺序处理：

1. 双方签字并版本化的正式接口契约；
2. 厂商官方文档和真实联调环境脱敏报文；
3. 当前 FastAPI OpenAPI 和代码行为；
4. 本文档中的目标设计；
5. Mock 行为。

所有标记为待实现或待现场确认的内容都不能直接作为生产接口事实。接口实现或字段发生变化时，必须同步更新本文档、OpenAPI 契约测试和脱敏报文样例。
