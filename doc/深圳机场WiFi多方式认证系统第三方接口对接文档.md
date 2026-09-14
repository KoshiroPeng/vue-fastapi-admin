# 深圳机场 WiFi 多方式认证系统第三方接口对接文档

| 项目 | 内容 |
| :--- | :--- |
| 文档版本 | V1.0 |
| 编制日期 | 2026-09-11 |
| 适用系统 | `vue-fastapi-admin` / 深圳机场 WiFi 认证前置服务 |
| 文档状态 | 联调基线；标记为“待确认”的内容不得直接作为生产契约 |

## 1. 文档范围

本文档只包含以下接口：

1. **第三方调用本系统**：机场取号机、第三方微信小程序调用本系统后端的接口。
2. **本系统调用第三方**：本系统 FastAPI 后端调用登机牌验证系统、护照 OCR 服务、华为 iMaster NCE-Campus 北向 API 的接口。
3. **第三方小程序兼容链路**：第三方微信小程序按既有 SOAP WebService 和 GET Query 契约调用本系统，由本系统原样代理到 NCE。该链路与登机牌、护照使用的 JSON 访客创建接口相互独立。

以下接口不在本文档范围内：

- Vue 管理后台调用本系统的用户、角色、菜单、权限、审计、看板等内部接口；
- 本系统 Portal 页面调用本系统的登机牌、护照、微信事务创建及状态查询接口；
- `/health/live`、`/health/ready` 等内部运维接口；
- 仅供开发环境使用的 Mock 接口。

## 2. 接口分类与当前状态

| 编号 | 标识 | 调用方向 | 接口 | 当前状态 |
| :--- | :--- | :--- | :--- | :--- |
| IN-01 | **【给第三方使用】** | 机场取号机 → 本系统 | `POST /api/v1/kiosk/create-guest` | 已实现并完成 Mock/Redis 测试；真实取号机、真实 NCE 未联调 |
| IN-02 | **【给第三方使用】** | 第三方微信小程序 → 本系统 | `POST /api/v1/portal/wechat/auth/callback` | 已实现并完成 Mock/Redis 测试；真实小程序签名和成功证明未联调 |
| OUT-01 | **【调用第三方】** | 本系统 → 登机牌验证系统 | `POST /api/v1/boarding-pass/verify` | 仅有设计契约、Protocol 和 Mock；真实客户端未实现 |
| OUT-02 | **【调用第三方】** | 本系统 → 护照 OCR 服务 | `POST {OCR_BASE_URL}/xxx/doAllCardFileRecon` | 仅有设计契约、Protocol 和 Mock；厂商契约及真实客户端未实现 |
| OUT-03 | **【调用第三方】** | 本系统 → NCE 北向 API | `POST /controller/v2/tokens` | 契约基线已整理；真实 NCE 客户端未实现 |
| OUT-04 | **【调用第三方】** | 本系统 → NCE 北向 API | `GET /controller/campus/v2/accountservice/accessuser/users` | 契约基线已整理；真实 NCE 客户端未实现 |
| OUT-05 | **【调用第三方】** | 本系统 → NCE 北向 API | `POST /controller/campus/v2/accountservice/accessuser/guest` | 契约基线已整理；真实 NCE 客户端未实现 |
| OUT-06 | **【调用第三方】** | 本系统 → NCE 北向 API | `POST /controller/campus/v1/accountservice/user/radiuslog` | 契约基线已整理；真实 NCE 客户端未实现 |
| IN-03 | **【给第三方使用】** | 第三方微信小程序 → 本系统 → NCE | `POST /secoWS/service/NewGuestManagerServices` | 已实现 SOAP/XML 原样代理；真实 NCE 待联调 |
| IN-04 | **【给第三方使用】** | 第三方微信小程序 → 本系统 → NCE | `GET /PortalServer/AppPortalAuth?messageType=authRequest` | 已实现 Query 和 JSON 响应原样代理；真实 NCE 待联调 |
| IN-05 | **【给第三方使用】** | 第三方微信小程序 → 本系统 → NCE | `GET /PortalServer/AppPortalAuth?messageType=syncPortalAuthResultRequest` | 已实现 Query 和 JSON 响应原样代理；真实 NCE 待联调 |

> 重要说明：当前生产配置要求关闭 NCE、登机牌和 OCR Mock，但仓库中尚无对应真实适配器。OUT-01 至 OUT-06 目前是联调契约，不代表生产代码已经能够发出这些请求。

## 3. 通用约定

### 3.1 网络与编码

- 生产环境统一使用 HTTPS 或双方批准的受控专网。
- JSON 编码统一为 UTF-8。
- 日期时间使用 ISO 8601，并显式携带时区，例如 `2026-09-11T17:00:00+08:00`。
- Unix 时间戳如无特别说明使用秒；NCE 部分字段明确使用毫秒。
- MAC 地址对外建议使用 `AA-BB-CC-DD-EE-FF`，本系统接收后会执行标准化。

### 3.2 本系统统一响应

本系统成功响应：

```json
{
  "code": 200,
  "msg": "OK",
  "data": {}
}
```

本系统普通错误响应：

```json
{
  "code": 400,
  "msg": "错误说明",
  "data": null
}
```

本系统参数校验失败响应：

```json
{
  "code": 422,
  "msg": "请求参数校验失败",
  "data": {
    "errors": [
      {
        "type": "string_pattern_mismatch",
        "loc": ["body", "idDigest"],
        "msg": "String should match pattern"
      }
    ]
  },
  "error_code": "REQUEST_INVALID"
}
```

本系统风控错误响应：

```json
{
  "code": 409,
  "msg": "请求已处理，请勿重复提交",
  "data": null,
  "error_code": "REPLAY_DETECTED"
}
```

### 3.3 请求追踪

- 调用方可传入 `X-Request-ID`，格式为 1～64 位字母、数字、点、下划线、冒号或连字符。
- 未提供或格式非法时，本系统自动生成请求 ID。
- 本系统在响应 Header 中返回最终使用的 `X-Request-ID`。
- 第三方排障时必须同时提供请求时间、`X-Request-ID`、HTTP 状态码和业务错误码，不得提供密码、Token、完整证件信息或原始护照图片。

### 3.4 敏感信息要求

禁止写入日志、工单或普通聊天工具的内容：

- 访客密码、管理员密码；
- NCE `x-access-token`、XSRF Token、Cookie；
- 短信验证码；
- 护照原图和 OCR 原始完整报文；
- 完整证件号码、证件后四位明文、手机号；
- 生产 HMAC 密钥、OAuth Client Secret、私钥。

---

# 第一部分：第三方调用本系统

## 4. IN-01【给第三方使用】取号机创建临时访客

### 4.1 基本信息

| 项目 | 内容 |
| :--- | :--- |
| 调用方 | 机场现场取号机 |
| 提供方 | 本系统 FastAPI |
| Method | `POST` |
| Path | `/api/v1/kiosk/create-guest` |
| Content-Type | `application/json` |
| 鉴权方式 | 来源 IP 白名单 + HMAC-SHA256 + 时间戳 + Nonce + 幂等键 |
| 最大请求体 | 默认 8192 字节，以部署配置 `KIOSK_MAX_BODY_BYTES` 为准 |
| 当前状态 | 接口代码已实现；真实设备签名规范、生产密钥和真实 NCE 尚待联调 |

生产 URL 示例：

```text
https://{system-domain}/api/v1/kiosk/create-guest
```

### 4.2 请求 Header

| Header | 类型 | 必填 | 约束 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `Content-Type` | string | 是 | 固定 `application/json` | 请求体格式 |
| `Content-Length` | integer | 是（当前联调要求） | 0～`KIOSK_MAX_BODY_BYTES` | 当前应用层按该 Header 校验大小；Nginx 同时限制 8KB |
| `X-Kiosk-Id` | string | 是 | 1～64 位；正则 `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$` | 取号机唯一编号 |
| `X-Timestamp` | string | 是 | 1～20 位，可解析为正整数 | Unix 秒级时间戳；默认允许服务器时间正负 300 秒偏差 |
| `X-Nonce` | string | 是 | 8～128 字符 | 每次请求唯一随机数；默认 300 秒内不得重复 |
| `X-Signature` | string | 是 | 64 字符 | HMAC-SHA256 十六进制签名 |
| `Idempotency-Key` | string | 是 | 8～128 字符 | 同一业务操作使用同一个键；默认 300 秒内不得重复占用 |
| `X-Request-ID` | string | 否 | 1～64 位安全字符 | 链路追踪编号 |

`X-Forwarded-For` 只能由受信任的 Nginx 覆盖写入，取号机不得自行构造或追加该 Header。

当前实现使用一个全局 `KIOSK_HMAC_SECRET`，尚未按 `X-Kiosk-Id` 分配独立密钥。来源白名单 `KIOSK_ALLOWED_IPS` 当前只支持精确 IP 字符串匹配，不支持 CIDR；代理信任列表 `TRUSTED_PROXY_IPS` 支持单 IP 或 CIDR。

### 4.3 请求 Body

```json
{
  "idType": "ID_CARD",
  "idDigest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

| 字段 | 类型 | 必填 | 约束 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `idType` | string | 是 | `ID_CARD` 或 `PASSPORT` | 证件类型 |
| `idDigest` | string | 是 | 64 位小写十六进制 | 证件标识摘要；不得传完整证件号或可逆密文 |

请求体禁止出现未定义字段。

当前代码只校验 `idType` 和 `idDigest`，路由处理函数没有继续使用这两个字段；内部操作编号由 `Idempotency-Key` 的 SHA-256 前 16 位生成。第三方不得假设返回账号一定由 `idDigest` 派生。

当前应用代码只在存在 `Content-Length` 时检查声明大小，未对无长度的分块请求再次累计限制。第三方联调必须发送正确的 `Content-Length`，生产入口必须保留 Nginx 8KB 限制。

### 4.4 签名算法

先计算原始请求体字节的 SHA-256：

```text
bodyDigest = hex_lowercase(SHA256(rawRequestBodyBytes))
```

再使用换行符 `\n` 按以下顺序拼接签名原文，末尾不追加换行：

```text
POST
/api/v1/kiosk/create-guest
{X-Kiosk-Id}
{X-Timestamp}
{X-Nonce}
{Idempotency-Key}
{bodyDigest}
```

计算签名：

```text
X-Signature = hex_lowercase(
  HMAC-SHA256(kioskSecret, canonicalRequestUtf8Bytes)
)
```

注意事项：

- 必须使用实际发送的原始 JSON 字节计算摘要。
- JSON 空格、字段顺序、换行或字符编码变化都会改变签名。
- 签名绑定 Method、Path、取号机编号、时间戳、Nonce、幂等键和请求体。
- 生产密钥不得使用测试向量中的密钥。

### 4.5 非生产联调测试向量

```text
secret         = test-kiosk-secret
method         = POST
path           = /api/v1/kiosk/create-guest
X-Kiosk-Id     = KIOSK-T3-001
X-Timestamp    = 1789027200
X-Nonce        = nonce-001
Idempotency-Key= request-001
rawBody        = {"idType":"ID_CARD","idDigest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
expectedSign   = f71670fd3f13031403e985ebd7deb4c9ffe38be184a0474181046c63c338888e
```

该测试密钥和固定时间戳只能用于双方离线校验签名实现，不能用于生产请求。

### 4.6 成功响应

HTTP `200 OK`

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "username": "kiosk_98fc1c14",
    "password": "88482026",
    "validDurationMinutes": 1440,
    "expireTime": "2026-09-12T17:00:00+08:00",
    "maxDevices": 1,
    "ssid": "Airport-Free-WiFi"
  }
}
```

| 字段 | 类型 | 必返 | 说明 |
| :--- | :--- | :--- | :--- |
| `code` | integer | 是 | HTTP 状态码对应的业务码；成功为 200 |
| `msg` | string | 是 | 成功默认为 `OK` |
| `data.username` | string | 是 | NCE 临时访客账号 |
| `data.password` | string | 是 | 临时密码；只能展示或打印，不得落日志 |
| `data.validDurationMinutes` | integer | 是 | 有效时长，默认 1440 分钟 |
| `data.expireTime` | string | 是 | 失效时间，ISO 8601 |
| `data.maxDevices` | integer | 是 | 最大终端数，当前固定为 1 |
| `data.ssid` | string | 是 | 旅客应连接的 SSID |

### 4.7 错误响应

| HTTP | `error_code`/场景 | 说明 | 调用方处理 |
| :--- | :--- | :--- | :--- |
| 400 | Content-Length 非法、来源地址格式非法 | 请求格式错误 | 修正请求，不重试原报文 |
| 401 | 签名无效 | HMAC 校验失败 | 检查密钥、原始 Body、字段顺序和 Path |
| 401 | `REQUEST_EXPIRED` | 时间戳过期或时钟偏差超限 | 校时后使用新 Timestamp、Nonce、幂等键重试 |
| 403 | 来源 IP 不在白名单 | 取号机出口地址未授权 | 联系运维配置白名单 |
| 409 | `REPLAY_DETECTED` | Nonce 已使用 | 生成新 Nonce；不得重复发送原请求 |
| 409 | `IDEMPOTENCY_CONFLICT` | 幂等键正在处理或已被占用 | 不得盲目换键重复创建账号；先人工核实结果 |
| 413 | 请求体过大 | 超过配置上限 | 缩减请求体 |
| 422 | `REQUEST_INVALID` | Header 或 Body 字段校验失败 | 根据 `data.errors` 修正字段 |
| 429 | `RATE_LIMITED` | 超过来源 IP 频率限制 | 按响应 Header `Retry-After` 等待后重试 |
| 502 | `NCE_AUTHENTICATION_FAILED` / `NCE_BUSINESS_ERROR` / `NCE_UNAVAILABLE` | NCE 鉴权、业务或可用性异常 | 保留请求 ID，联系系统运维 |
| 504 | `NCE_TIMEOUT` | NCE 响应超时 | 查询是否已创建账号后再决定是否重试 |
| 503 | 安全配置缺失 | HMAC 或摘要密钥未配置 | 不重试，联系系统运维 |

> 当前幂等实现只占用键，不保存执行结果。发生“NCE 已创建成功但响应丢失”时，重复请求可能返回 409，第三方不得通过更换幂等键直接重建账号。

### 4.8 调用示例

```bash
BODY='{"idType":"ID_CARD","idDigest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'

curl -X POST 'https://{system-domain}/api/v1/kiosk/create-guest' \
  -H 'Content-Type: application/json' \
  -H 'X-Kiosk-Id: kiosk-001' \
  -H 'X-Timestamp: {unix-seconds}' \
  -H 'X-Nonce: {unique-nonce}' \
  -H 'Idempotency-Key: {business-request-id}' \
  -H 'X-Signature: {hmac-sha256-hex}' \
  --data-binary "$BODY"
```

---

## 5. IN-02【给第三方使用】微信小程序认证状态回写

### 5.1 基本信息

| 项目 | 内容 |
| :--- | :--- |
| 调用方 | 第三方微信小程序后端或受信任回调服务 |
| 提供方 | 本系统 FastAPI |
| Method | `POST` |
| Path | `/api/v1/portal/wechat/auth/callback` |
| Content-Type | `application/json` |
| 鉴权方式 | HMAC-SHA256 + 时间戳 + Nonce 防重放 |
| 前置条件 | `authTxId` 必须由本系统 Portal 流程预先创建，并处于允许回写的状态 |
| 当前状态 | 已实现并完成 Mock/Redis 测试；真实小程序签名规范和 NCE 成功证明待联调 |

### 5.2 请求 Header

| Header | 类型 | 必填 | 约束 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `Content-Type` | string | 是 | 固定 `application/json` | 请求体格式 |
| `X-Wx-Signature` | string | 是 | 64 字符 | HMAC-SHA256 十六进制签名 |
| `X-Wx-Timestamp` | string | 是 | 1～20 位，可解析为正整数 | Unix 秒级时间戳；默认正负 300 秒偏差 |
| `X-Wx-Nonce` | string | 是 | 8～128 字符 | 单次随机数；默认 300 秒内不得重复 |
| `X-Request-ID` | string | 否 | 1～64 位安全字符 | 链路追踪编号 |

### 5.3 请求 Body

```json
{
  "authTxId": "3fe34d91c6924cbca3307f42f71d9501",
  "result": "SUCCESS",
  "nceSuccess": true
}
```

| 字段 | 类型 | 必填 | 约束 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `authTxId` | string | 是 | 1～64 字符 | 本系统预先创建的认证事务编号 |
| `result` | string | 是 | `SUCCESS` 或 `FAILED` | 小程序认证结果 |
| `nceSuccess` | boolean | 是 | `true` 或 `false` | NCE Portal 是否已经明确完成放行 |

当前代码禁止额外字段。旧设计中的 `clientMac`、`clientIp`、`message` 不属于当前实现的请求模型，不得发送。

### 5.4 签名算法

先计算原始请求体摘要：

```text
bodyDigest = hex_lowercase(SHA256(rawRequestBodyBytes))
```

签名原文：

```text
{X-Wx-Timestamp}
{X-Wx-Nonce}
{bodyDigest}
```

计算签名：

```text
X-Wx-Signature = hex_lowercase(
  HMAC-SHA256(wechatCallbackSecret, canonicalRequestUtf8Bytes)
)
```

要求：

- 使用实际发送的原始 Body 字节计算摘要。
- 生产回调密钥通过安全渠道交付，不得写入前端、小程序包或日志。
- 同一 Nonce 在有效期内只能使用一次。
- 只有 `result=SUCCESS` 且 `nceSuccess=true` 时，本系统才把事务更新为 `SUCCESS`；其他组合更新为 `FAILED`。
- 当前使用一个全局 `WECHAT_CALLBACK_SECRET`，未按小程序、租户或调用方分配独立密钥。
- 当前系统把 `nceSuccess` 视为可信调用方声明，不会在回调处理中再次查询 NCE。正式联调必须明确可验证的 NCE 成功凭证或调用方责任边界。

### 5.5 成功响应

HTTP `200 OK`

```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "authTxId": "3fe34d91c6924cbca3307f42f71d9501",
    "status": "SUCCESS"
  }
}
```

| 字段 | 类型 | 必返 | 说明 |
| :--- | :--- | :--- | :--- |
| `data.authTxId` | string | 是 | 原认证事务编号 |
| `data.status` | string | 是 | 最终状态：`SUCCESS` 或 `FAILED` |

### 5.6 错误响应

| HTTP | `error_code`/场景 | 说明 |
| :--- | :--- | :--- |
| 401 | 微信回写时间戳无效 | Timestamp 不能转换为整数 |
| 401 | `REQUEST_EXPIRED` | 时间戳过期或时钟偏差超限 |
| 401 | 微信状态回写签名无效 | HMAC 校验失败或业务服务拒绝回写 |
| 409 | `REPLAY_DETECTED` | Nonce 已使用 |
| 422 | `REQUEST_INVALID` | Header 或 Body 字段校验失败 |
| 500（当前实现风险） | 事务不存在、已过期或状态不允许转换 | 当前事务异常尚未映射为稳定的 404/409，对接前必须冻结最终错误语义 |
| 503/500 | Redis 或回调密钥配置异常 | 联系系统运维，不得无界重试 |

### 5.7 调用顺序

```text
1. 本系统 Portal 创建 authTxId
2. 微信小程序调用本系统 SOAP 兼容接口添加访客
3. 微信小程序调用本系统 AppPortalAuth 兼容接口发起认证
4. 微信小程序调用同一兼容接口同步认证结果
5. 只有 NCE 明确返回成功后，小程序调用本接口：result=SUCCESS、nceSuccess=true
6. 本系统返回 status=SUCCESS
7. Portal 页面通过本系统内部状态查询接口显示联网成功
```

### 5.8 调用示例

```bash
BODY='{"authTxId":"3fe34d91c6924cbca3307f42f71d9501","result":"SUCCESS","nceSuccess":true}'

curl -X POST 'https://{system-domain}/api/v1/portal/wechat/auth/callback' \
  -H 'Content-Type: application/json' \
  -H 'X-Wx-Timestamp: {unix-seconds}' \
  -H 'X-Wx-Nonce: {unique-nonce}' \
  -H 'X-Wx-Signature: {hmac-sha256-hex}' \
  --data-binary "$BODY"
```

---

# 第二部分：本系统调用第三方

## 6. OUT-01【调用第三方】登机牌三要素验证

### 6.1 基本信息

| 项目 | 内容 |
| :--- | :--- |
| 提供方 | 第三方登机牌验证系统 |
| 调用方 | 本系统 FastAPI |
| Method | `POST` |
| Path | `/api/v1/boarding-pass/verify` |
| Content-Type | `application/json` |
| 建议鉴权 | 双向 TLS；或 OAuth 2.0 Client Credentials + IP 白名单 |
| 超时基线 | 3 秒 |
| 幂等要求 | 同一 `requestId` 重试必须返回一致结果 |
| 当前状态 | 契约待第三方确认；真实 HTTP 客户端未实现，当前仅 Protocol + Mock |

Base URL、证书、OAuth 地址、Client ID、Client Secret 均由第三方通过受控渠道提供。

### 6.2 请求 Body

```json
{
  "requestId": "b861d04d-10bf-45ab-bae9-7756aa588401",
  "requestTime": "2026-09-11T17:00:00+08:00",
  "airportCode": "SZX",
  "flightDate": "2026-09-11",
  "flightNo": "CA1234",
  "seatNo": "16A",
  "documentLast4": "5678",
  "clientId": "SZX_WIFI_PORTAL"
}
```

| 字段 | 类型 | 必填 | 约束 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `requestId` | string | 是 | UUID，最长 64 字符 | 幂等、追踪和审计编号 |
| `requestTime` | string | 是 | ISO 8601，含时区 | 请求时间 |
| `airportCode` | string | 是 | 固定 `SZX` | 机场代码 |
| `flightDate` | string | 是 | `YYYY-MM-DD` | 深圳出港当地日期 |
| `flightNo` | string | 是 | 正则 `^[A-Za-z0-9]{2,3}\d{3,4}$` | 去空格并转大写 |
| `seatNo` | string | 是 | 正则 `^\d{1,2}[A-Za-z]$` | 去空格并转大写 |
| `documentLast4` | string | 是 | 4 位字母或数字 | 购票/值机证件号码后四位 |
| `clientId` | string | 是 | 双方分配 | 本系统调用方标识 |

### 6.3 成功响应

HTTP `200 OK`

```json
{
  "requestId": "b861d04d-10bf-45ab-bae9-7756aa588401",
  "success": true,
  "verified": true,
  "code": "0000",
  "message": "Verified",
  "flightStatus": "BOARDING",
  "validUntil": "2026-09-11T20:00:00+08:00",
  "responseTime": "2026-09-11T17:00:01+08:00"
}
```

| 字段 | 类型 | 必返 | 说明 |
| :--- | :--- | :--- | :--- |
| `requestId` | string | 是 | 原样返回请求 ID |
| `success` | boolean | 是 | 接口是否正常完成处理，不等同于验证通过 |
| `verified` | boolean | 是 | 三要素及业务规则是否验证通过 |
| `code` | string | 是 | 业务结果码 |
| `message` | string | 是 | 简短说明，不得包含个人敏感信息 |
| `flightStatus` | string | 否 | `NORMAL`、`DELAYED`、`BOARDING`、`DEPARTED`、`CANCELLED`、`UNKNOWN` |
| `validUntil` | string | 否 | 验证结果建议有效截止时间，ISO 8601 |
| `responseTime` | string | 是 | 第三方响应时间，ISO 8601 |

### 6.4 结果码

| code | 含义 | 本系统处理 |
| :--- | :--- | :--- |
| `0000` | 验证通过 | 仅当 `success=true` 且 `verified=true` 时创建 NCE 临时访客 |
| `1001` | 验证未通过 | 不创建访客，对旅客展示统一失败提示 |
| `1002` | 不在适用航班范围 | 不创建访客，提示选择其他认证方式 |
| `1003` | 登机牌无效、取消或作废 | 不创建访客，不暴露具体不匹配字段 |
| `1004` | 超出允许认证时间窗口 | 不创建访客 |
| `2001` | 请求字段或格式错误 | 不重试 |
| `2002` | 鉴权失败或无权访问 | 记录安全告警，不向旅客暴露详情 |
| `3001` | 第三方数据源不可用 | 按双方约定有限重试，随后降级 |
| `3002` | 处理超时 | 按双方约定有限重试，随后降级 |

### 6.5 当前实现差异

当前 `BoardingPassClient` 仅定义以下内部字段：

- 请求：`flight_date`、`flight_no`、`seat_no`、`document_last4`、`client_ip`、`client_mac`、`ssid`；
- 响应：`verified`、`result_code`、`valid_until`。

真实适配器实现前必须明确：

1. `requestId/requestTime/airportCode/clientId` 的生成和映射；
2. 鉴权方式、证书或 OAuth Token 获取方式；
3. HTTP 状态码与业务结果码的组合规则；
4. 重试次数、重试条件和幂等保留期；
5. 完整成功及失败报文样例。

---

## 7. OUT-02【调用第三方】护照 OCR 文件流识别

### 7.1 基本信息

| 项目 | 内容 |
| :--- | :--- |
| 提供方 | 第三方 OCR 服务 |
| 调用方 | 本系统 FastAPI |
| Method | `POST` |
| URL | `{OCR_BASE_URL}/xxx/doAllCardFileRecon` |
| Content-Type | `multipart/form-data` |
| 超时基线 | 4 秒 |
| 当前状态 | 厂商 URL、鉴权、`typeId`、原始响应字段待确认；真实客户端未实现，当前仅 Protocol + Mock |

### 7.2 Form-Data

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `username` | string | 是 | OCR 服务白名单用户名，由安全配置注入 |
| `file` | binary | 是 | 护照 JPG 或 PNG 原始图片流；本系统入口最大 4MB |
| `typeId` | string/integer | 是 | 护照产品类型编码，具体类型和取值由 OCR 厂商确认 |

请求示例：

```bash
curl -X POST '{OCR_BASE_URL}/xxx/doAllCardFileRecon' \
  -F 'username={ocr-username}' \
  -F 'typeId={passport-type-id}' \
  -F 'file=@passport.jpg;type=image/jpeg'
```

### 7.3 厂商原始响应

厂商原始响应结构尚未冻结，不得在实现中假设未确认字段。当前已知状态规则：

| status | 含义 | 本系统处理 |
| :--- | :--- | :--- |
| `2` | 证件识别成功 | 提取护照号和 MRZ，执行本地 MRZ 校验 |
| `-1` | 识别失败 | 返回统一重新拍摄提示 |
| `-2` | 未检测到可识别证件 | 返回统一重新拍摄提示 |
| `-6` | 图像被拒识 | 返回图片质量不合格提示 |
| `0` | 其他识别类接口成功 | 仅在厂商确认适用于当前产品时采用 |
| 其他 | 识别失败 | 映射为上游业务失败 |

### 7.4 本系统内部归一化模型

真实适配器必须把厂商响应转换为以下内部数据，不得把原始 OCR 报文返回给浏览器：

```json
{
  "passportNumber": "E00001234",
  "mrzValid": true,
  "resultCode": "2"
}
```

| 字段 | 类型 | 必返 | 说明 |
| :--- | :--- | :--- | :--- |
| `passportNumber` | string | 是 | 仅在内存中短时使用，日志禁止输出 |
| `mrzValid` | boolean | 是 | ICAO MRZ 校验结果 |
| `resultCode` | string | 是 | 厂商结果码的字符串形式 |

### 7.5 待第三方确认项

- 真实 Base URL、TLS 证书及网络白名单；
- 除 `username` 外是否还需要密码、Token、签名或 Client ID；
- 护照对应的 `typeId`；
- 文件字段名称、文件名及 MIME 要求；
- 原始成功/失败 JSON 或 XML 完整结构；
- 护照号、MRZ、国家、有效期字段位置；
- 错误码、HTTP 状态码、超时、并发和限流要求；
- 厂商是否保存原图及其销毁、审计和合规策略。

---

## 8. NCE 北向 API 通用约定

### 8.1 基地址

```text
NCE_BASE_URL=https://{nce-host}:{northbound-port}
```

北向 API 与 NCE Portal 认证 API 必须使用不同配置项：

- `NCE_BASE_URL`：Token、用户、访客、RADIUS 日志等北向接口；
- `NCE_PORTAL_AUTH_BASE_URL`：微信小程序 Portal 认证接口。

### 8.2 北向鉴权

除 Token 接口外，请求 Header 携带：

```http
x-access-token: {token}
Accept: application/json
```

Token 禁止写入 URL、日志和浏览器。

### 8.3 当前实现状态

代码目前仅定义 `NCEClient` Protocol 和 Mock。关闭 `NCE_MOCK_ENABLED` 后会直接抛出“真实 NCE 客户端尚未配置”。以下接口报文属于设计及联调基线，真实适配器、证书校验、Token 缓存、刷新和重试尚未落地。

---

## 9. OUT-03【调用第三方】获取 NCE Token

### 9.1 请求

| 项目 | 内容 |
| :--- | :--- |
| Method | `POST` |
| URI | `/controller/v2/tokens` |
| Content-Type | `application/json` |
| 鉴权 | NCE 三方系统接入用户名和密码 |

```json
{
  "userName": "{nce-username}",
  "password": "{nce-password}"
}
```

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `userName` | string | 是 | NCE 三方系统接入用户 |
| `password` | string | 是 | NCE 接入密码，必须从 Secret 注入 |

### 9.2 响应

Token 可能位于：

1. 响应 Header `x-access-token`；或
2. 响应 Body 的 `token` / `token_id` 字段。

具体返回位置必须以现场 NCE 版本实测为准。

本系统内部归一化为：

```json
{
  "value": "{secret-token}",
  "expiresAt": "2026-09-11T17:30:00+08:00"
}
```

Token 预计有效期约 1800 秒，但有效期来源、提前刷新时间及并发刷新规则必须现场确认。

### 9.3 异常处理

| 场景 | 本系统处理基线 |
| :--- | :--- |
| 用户名或密码错误 | 映射为 `NCE_AUTHENTICATION_FAILED`，不记录密码和原始响应 |
| HTTP 401/403 | 记录安全告警，停止业务请求 |
| 网络不可达 | 映射为 `NCE_UNAVAILABLE` |
| 超时 | 映射为 `NCE_TIMEOUT` |
| 业务请求发现 Token 失效 | 仅允许刷新一次 Token，并使用原请求幂等标识重试一次 |

---

## 10. OUT-04【调用第三方】查询 NCE 用户/在线终端

### 10.1 请求

| 项目 | 内容 |
| :--- | :--- |
| Method | `GET` |
| URI | `/controller/campus/v2/accountservice/accessuser/users` |
| 鉴权 | Header `x-access-token` |

Query 参数：

| 参数 | 类型 | 必填 | 约束/默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `userName` | string | 否 | 最长 128 | 用户名精准或模糊查询，匹配语义待 NCE 确认 |
| `userGroupId` | string | 否 | 最长 64 | 用户组 ID |
| `pageIndex` | integer | 是 | >= 1 | 页码 |
| `pageSize` | integer | 是 | 1～200；建议 20 或 50 | 每页数量 |
| 在线过滤参数 | 待确认 | 否 | 待现场契约确认 | 代码存在 `online_only` 内部字段，但 NCE 原始 Query 名称尚未冻结 |

示例：

```http
GET {NCE_BASE_URL}/controller/campus/v2/accountservice/accessuser/users?userName=guest&userGroupId={group-id}&pageIndex=1&pageSize=20
x-access-token: {token}
Accept: application/json
```

### 10.2 本系统期望的归一化响应

NCE 原始响应字段包装层尚待现场确认。真实适配器至少需要归一化为：

```json
{
  "items": [
    {
      "id": "user-id",
      "userName": "guest001",
      "userGroupId": "group-id",
      "userGroupName": "Guest",
      "userTypeCode": 20,
      "isOnline": true,
      "terminalIp": "10.85.73.8",
      "terminalMac": "AA-BB-CC-DD-EE-FF",
      "accessSsid": "Airport-Free-WiFi",
      "connectedAt": "2026-09-11T16:00:00+08:00"
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 20
}
```

| 字段 | 类型 | 必返 | 说明 |
| :--- | :--- | :--- | :--- |
| `items[].id` | string | 是 | NCE 用户唯一标识 |
| `items[].userName` | string | 是 | 用户名；对管理端返回前应脱敏 |
| `items[].userGroupId` | string | 是 | 用户组 ID |
| `items[].userGroupName` | string | 是 | 用户组名称 |
| `items[].userTypeCode` | integer | 是 | NCE 用户类型代码 |
| `items[].isOnline` | boolean | 是 | 是否在线 |
| `items[].terminalIp` | string/null | 否 | 终端 IP；对管理端返回前应脱敏 |
| `items[].terminalMac` | string/null | 否 | 终端 MAC；对管理端返回前应脱敏 |
| `items[].accessSsid` | string/null | 否 | 接入 SSID |
| `items[].connectedAt` | string/null | 否 | 上线时间，ISO 8601 |
| `total` | integer | 是 | 总记录数 |
| `page` | integer | 是 | 当前页 |
| `pageSize` | integer | 是 | 每页数量 |

---

## 11. OUT-05【调用第三方】创建 NCE 临时访客

### 11.1 请求

| 项目 | 内容 |
| :--- | :--- |
| Method | `POST` |
| URI | `/controller/campus/v2/accountservice/accessuser/guest` |
| 鉴权 | Header `x-access-token` |
| Content-Type | `application/json` |
| 成功 HTTP 状态 | 设计基线为 `201 Created`，以现场版本实测为准 |

Header：

```http
x-access-token: {token}
Content-Type: application/json
Accept: application/json
```

Body 字段：

| 字段 | 类型 | 必填 | 约束/取值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `userType` | int32 | 是 | 固定 `20` | 普通访客账号密码类型 |
| `userName` | string | 是 | 最长 128；不得包含 `=+%,#" ` 等特殊字符 | 临时访客账号 |
| `password` | string | 是 | 8～12 位复杂字符，以 NCE 现场策略为准 | 临时密码，不得记录日志 |
| `userGroupId` | string | 是 | 配置注入 | NCE 访客用户组 ID |
| `effectiveType` | int32 | 否 | `0` 创建时生效；`1` 首次登录生效 | 生效方式 |
| `validPeriodLong` | int64 | 条件必填 | 毫秒时间戳 | `effectiveType=0` 时使用 |
| `effectiveUnit` | string | 条件必填 | `hour`、`day`、`min` | `effectiveType=1` 时使用 |
| `effectiveTime` | int32 | 条件必填 | 正整数 | 首次登录后的有效时长 |
| `maxAccessNum` | string | 否 | 当前业务固定 `"1"`；`"-1"` 表示不限制 | 最大接入终端数 |
| `accessType` | string | 否 | `deny` | 达到最大接入数后的策略 |
| `nextUpdateUserpass` | boolean | 否 | 当前固定 `false` | 下次登录是否要求改密 |
| `bindInfo` | object | 否 | — | 终端绑定信息 |
| `bindInfo.bindMac` | string | 否 | 合法 MAC | 绑定终端 MAC |
| `description` | string | 否 | 最长 128 | 脱敏业务备注 |

取号机场景示例：

```json
{
  "userType": 20,
  "userName": "kiosk_98fc1c14",
  "password": "{generated-secret}",
  "userGroupId": "{guest-user-group-id}",
  "effectiveType": 1,
  "effectiveUnit": "hour",
  "effectiveTime": 24,
  "maxAccessNum": "1",
  "accessType": "deny",
  "nextUpdateUserpass": false,
  "description": "Kiosk Self-service 24h Guest"
}
```

登机牌场景示例：

```json
{
  "userType": 20,
  "userName": "bp_8f4b23d9",
  "password": "{generated-secret}",
  "userGroupId": "{guest-user-group-id}",
  "effectiveType": 0,
  "validPeriodLong": 1789142400000,
  "maxAccessNum": "1",
  "accessType": "deny",
  "nextUpdateUserpass": false,
  "bindInfo": {
    "bindMac": "AA-BB-CC-DD-EE-FF"
  },
  "description": "BoardingPass Three-Factor Verified"
}
```

护照场景示例：

```json
{
  "userType": 20,
  "userName": "pass_E12345678",
  "password": "{generated-secret}",
  "userGroupId": "{guest-user-group-id}",
  "effectiveType": 0,
  "validPeriodLong": 1789142400000,
  "maxAccessNum": "1",
  "accessType": "deny",
  "nextUpdateUserpass": false,
  "bindInfo": {
    "bindMac": "AA-BB-CC-DD-EE-FF"
  },
  "description": "Passport OCR Verified 8h Guest"
}
```

### 11.2 响应

```json
{
  "errcode": "0",
  "errmsg": "",
  "data": {
    "id": "38235d53-759d-4805-bf60-e8afa8ce5198",
    "userType": 20,
    "userName": "guest001",
    "password": null,
    "userGroupId": "{guest-user-group-id}",
    "effectiveType": 0,
    "validPeriodLong": 1789142400000,
    "maxAccessNum": "1",
    "accessType": "deny"
  }
}
```

| 字段 | 类型 | 必返 | 说明 |
| :--- | :--- | :--- | :--- |
| `errcode` | string | 是 | `0` 表示成功，其他值为 NCE 业务错误 |
| `errmsg` | string | 是 | NCE 错误说明；不得原样返回旅客端 |
| `data.id` | string | 成功时 | NCE 访客 ID |
| `data.userType` | integer | 成功时 | 用户类型 |
| `data.userName` | string | 成功时 | 访客账号 |
| `data.password` | string/null | 否 | NCE 可能不回传密码；本系统应使用本地刚生成的短时值 |
| `data.userGroupId` | string | 成功时 | 用户组 ID |
| `data.effectiveType` | integer | 成功时 | 生效方式 |
| `data.validPeriodLong` | integer/null | 否 | 毫秒级过期时间 |
| `data.maxAccessNum` | string | 成功时 | 最大终端数 |
| `data.accessType` | string | 成功时 | 超限策略 |

### 11.3 错误和重试原则

- Token 失效：刷新 Token 一次，并保持原业务请求标识重试一次。
- HTTP 5xx、网络错误或超时：只有在确认 NCE 按请求标识幂等时才允许有限重试。
- 创建访客响应丢失：必须先查询创建结果，禁止直接更换用户名或幂等键重复创建。
- NCE 业务失败：映射为 `NCE_BUSINESS_ERROR`，不得向旅客端暴露原始错误详情。

---

## 12. OUT-06【调用第三方】查询 NCE RADIUS 日志

### 12.1 请求

| 项目 | 内容 |
| :--- | :--- |
| Method | `POST` |
| URI | `/controller/campus/v1/accountservice/user/radiuslog` |
| 鉴权 | Header `x-access-token` |
| Content-Type | `application/json` |
| 查询跨度 | 不超过 7 天 |
| 分页方式 | `startRowKey` 游标分页 |

```json
{
  "logType": "authen",
  "siteId": "{site-id}",
  "queryMode": "ONE_SITE",
  "authenResultCode": 1,
  "failReasonCode": 0,
  "authenStartTime": 1789056000000,
  "authenEndTime": 1789142399000,
  "userTypeCode": -1,
  "authenTypeCode": -1,
  "pageSize": 101,
  "pageIndex": 1,
  "startRowKey": ""
}
```

| 字段 | 类型 | 必填 | 取值/约束 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `logType` | string | 是 | `authen` 或 `account` | 认证日志或计费日志 |
| `siteId` | string | 是 | 配置注入 | NCE 站点 ID |
| `queryMode` | string | 否 | 当前固定 `ONE_SITE` | 单站点查询 |
| `authenResultCode` | int32 | 是 | `0` 成功、`1` 失败 | 认证结果过滤 |
| `failReasonCode` | int32 | 否 | `0` 表示全部 | 失败原因过滤 |
| `authenStartTime` | int64 | 是 | 毫秒时间戳 | 查询开始时间 |
| `authenEndTime` | int64 | 是 | 毫秒时间戳 | 查询结束时间，必须晚于开始时间 |
| `userTypeCode` | int32 | 否 | `-1` 表示全部 | 用户类型过滤 |
| `authenTypeCode` | int32 | 否 | `-1` 表示全部 | 认证类型过滤 |
| `pageSize` | int32 | 是 | 当前固定 101，最大 101 | 每页条数 |
| `pageIndex` | int32 | 是 | 游标模式固定 1 | 页码 |
| `startRowKey` | string | 否 | 首次为空；后续传上页 `endRowKey` | 游标 |

### 12.2 响应

```json
{
  "errcode": "0",
  "errmsg": "",
  "startRowKey": "1529648614575D431E4891D734D68B89FD14BAC639C47",
  "endRowKey": "15296432844906C2BC8D50ED94D9A87C4660E418E6472",
  "totalSize": 101,
  "pageSize": 101,
  "pageIndex": 1,
  "data": [
    {
      "id": "1bfa53069969491bbe495fcbb65c486a",
      "userName": "bp_CZ3101_5678",
      "userGroupName": "Guest",
      "userTypeCode": 20,
      "terminalIpV4": "10.85.73.8",
      "terminalMac": "AA-BB-CC-DD-EE-FF",
      "authenTypeCode": 11,
      "accessSsid": "Airport-Free-WiFi",
      "authenTime": "1789100000000",
      "authenResultCode": 0,
      "failReasonCode": 0
    }
  ]
}
```

| 字段 | 类型 | 必返 | 说明 |
| :--- | :--- | :--- | :--- |
| `errcode` | string | 是 | `0` 表示成功 |
| `errmsg` | string | 是 | NCE 结果说明 |
| `startRowKey` | string/null | 否 | 当前页起始游标 |
| `endRowKey` | string/null | 否 | 下一页请求使用的游标 |
| `totalSize` | integer | 是 | 当前查询返回或可见总量，准确语义待现场确认 |
| `pageSize` | integer | 是 | 每页条数 |
| `pageIndex` | integer | 是 | 页码 |
| `data[].id` | string | 是 | 日志 ID |
| `data[].userName` | string | 是 | 用户名；返回管理端前脱敏 |
| `data[].userGroupName` | string | 是 | 用户组名称 |
| `data[].userTypeCode` | integer | 是 | 用户类型代码 |
| `data[].terminalIpV4` | string | 是 | 终端 IPv4；返回管理端前脱敏 |
| `data[].terminalMac` | string | 是 | 终端 MAC；返回管理端前脱敏 |
| `data[].authenTypeCode` | integer | 是 | 认证类型代码 |
| `data[].accessSsid` | string | 是 | 接入 SSID |
| `data[].authenTime` | string/integer | 是 | 毫秒时间戳；现场返回类型需确认 |
| `data[].authenResultCode` | integer | 是 | 0 成功，其他值按 NCE 契约解释 |
| `data[].failReasonCode` | integer | 是 | 失败原因代码 |

### 12.3 常用失败原因

| failReasonCode | 含义 | 业务处置 |
| :--- | :--- | :--- |
| `0` | 无失败或全部 | 正常处理 |
| `101` | 账号或密码错误 | 提示核对凭据或重新获取小票 |
| `105` | 连续密码错误导致锁定 | 提示稍后再试 |
| `106` / `149` | 访客账号过期 | 引导重新认证 |
| `108` | 超过最大接入数 | 提示设备数超限 |
| `111` | MAC 不匹配 | 拒绝非绑定设备 |
| `116` | 认证通信超时 | 提示重试 |
| `642` | 短信验证码错误或为空 | 提示验证码错误 |
| `643` | 短信验证码过期 | 重新获取验证码 |

---

# 第三部分：第三方微信小程序兼容接口

## 13. IN-03【给第三方使用】添加访客

> 本接口保留既有 SOAP WebService 契约。小程序调用本系统域名，本系统将 SOAP 报文原样转发到配置的 NCE 上游，不复用登机牌、护照的 JSON 访客创建适配器。

### 13.1 请求

| 项目 | 内容 |
| :--- | :--- |
| 提供方 | 本系统兼容代理 |
| 调用方 | 第三方微信小程序 |
| Method | `POST` |
| URI | `/secoWS/service/NewGuestManagerServices` |
| Content-Type | `application/soap+xml` |
| SOAP 操作 | `addGuestAccount` |

SOAP Body 中保留以下既有字段，字段名和含义不得调整：

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `account` | string | 是 | 访客账号 |
| `authPolicy` | string | 是 | 认证策略 |
| `changePwdAtNextLogin` | boolean/string | 是 | 下次登录是否修改密码 |
| `orgName` | string | 是 | 访客所属组织 |
| `password` | string | 是 | 访客密码，不得记录日志 |
| `validBeginPeriod` | string | 是 | 有效期开始时间 |
| `validPeriod` | string/integer | 是 | 有效时长 |

### 13.2 响应

本系统原样返回 NCE 的 HTTP 状态码、SOAP/XML 响应体和 `Content-Type`。既有调用方以 HTTP `statusCode == 200` 判断添加成功，不额外套用本系统 JSON 响应结构。

---

## 14. IN-04【给第三方使用】发起认证

### 14.1 请求

| 项目 | 内容 |
| :--- | :--- |
| 提供方 | 本系统兼容代理 |
| 调用方 | 第三方微信小程序 |
| Method | `GET` |
| URI | `/PortalServer/AppPortalAuth` |

| Query 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `messageType` | string | 是 | 固定为 `authRequest` |
| `userName` | string | 是 | 访客账号 |
| `password` | string | 是 | 访客密码；该兼容接口的访问日志必须关闭 |

### 14.2 响应

```json
{
  "resultCode": 0,
  "statusCode": 200,
  "sessionId": "{session-id}"
}
```

`resultCode=0` 表示接口调用成功。响应由 NCE 原样返回，不额外套用本系统 JSON 响应结构。

---

## 15. IN-05【给第三方使用】同步认证结果

### 15.1 请求

| 项目 | 内容 |
| :--- | :--- |
| 提供方 | 本系统兼容代理 |
| 调用方 | 第三方微信小程序 |
| Method | `GET` |
| URI | `/PortalServer/AppPortalAuth` |

| Query 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `messageType` | string | 是 | 固定为 `syncPortalAuthResultRequest` |
| `sessionId` | string | 是 | 发起认证成功后返回的会话 ID |

### 15.2 响应

```json
{
  "resultCode": 0,
  "portalAuthStatus": 1
}
```

`resultCode=0` 且 `portalAuthStatus=1` 表示认证成功。响应由 NCE 原样返回。

只有 IN-05 明确成功后，第三方微信小程序才能调用 IN-02，并提交：

```json
{
  "result": "SUCCESS",
  "nceSuccess": true
}
```

如果 IN-05 失败、超时或结果不确定，IN-02 不得提交成功状态。

---

## 16. 尚未形成可执行契约的外部接口

以下外部交互在设计中存在，但当前资料不足，不能编造接口地址或字段：

| 外部交互 | 当前缺失内容 | 责任方 |
| :--- | :--- | :--- |
| NCE Portal 用户名密码准入 | 提交地址、Method、隐藏字段、成功/失败标识 | NCE/网络团队 |
| NCE 原生短信认证 | 获取验证码和登录接口、DOM ID、隐藏字段、错误码 | NCE/网络团队 |
| NCE 在线用户过滤 | 真实在线过滤 Query 名称和原始响应包装结构 | NCE 团队 |
| NCE 主动踢线 | URI、权限边界、审计要求、请求/响应 | NCE/安全团队；未审批前不得启用 |
| OCR 原始响应 | URL、鉴权、`typeId`、字段和完整错误码 | OCR 厂商 |
| 登机牌验证接口 | Base URL、鉴权、完整报文、SLA、幂等期限 | 登机牌系统团队 |
| 微信回写成功证明 | 除 `nceSuccess` 布尔值外的可验证 NCE 成功凭证 | 微信小程序/NCE 团队 |

## 17. 联调验收清单

### 17.1 第三方调用本系统

- [ ] 双方 Base URL、HTTPS 证书、网络和白名单确认；
- [ ] 取号机离线签名测试向量一致；
- [ ] 服务器和第三方设备完成 NTP 校时；
- [ ] 正常、签名篡改、过期时间戳、Nonce 重放、幂等冲突、限流场景通过；
- [ ] 微信小程序完整执行 `addGuestAccount → authRequest → syncPortalAuthResultRequest → callback`；
- [ ] 三个兼容操作的请求字段、响应字段、状态码和 Content-Type 与既有契约一致；
- [ ] 回调失败时 Portal 不展示成功；
- [ ] 日志中无密码、Token、证件摘要明文和原始业务报文；
- [ ] 双方保存脱敏后的成功及失败报文样例。

### 17.2 本系统调用第三方

- [ ] 获取 NCE Token、Token 失效刷新和并发复用通过；
- [ ] NCE 创建访客正向、业务失败、超时和响应丢失场景通过；
- [ ] NCE 用户查询和 RADIUS 游标分页无重复、无漏项；
- [ ] 登机牌 `0000/1001/1002/1003/1004/2001/2002/3001/3002` 场景确认；
- [ ] OCR 成功、识别失败、无证件、拒识、超时场景确认；
- [ ] 所有外部调用均具有明确超时、有限重试、幂等和熔断规则；
- [ ] 真实第三方报文不会未经脱敏直接返回浏览器；
- [ ] 完成生产证书、账号、Token 和密钥轮换方案。

## 18. 实现与文档依据

- 第三方接口边界：`doc/深圳机场WiFi多方式认证系统详细设计说明书.md:718-756`
- 取号机设计契约：`doc/深圳机场WiFi多方式认证系统详细设计说明书.md:876-920`
- 登机牌第三方契约：`doc/深圳机场WiFi多方式认证系统详细设计说明书.md:924-996`
- OCR 第三方契约：`doc/深圳机场WiFi多方式认证系统详细设计说明书.md:1000-1028`
- NCE 北向及 Portal 契约：`doc/深圳机场WiFi多方式认证系统详细设计说明书.md:1032-1371`
- 取号机路由：`app/api/v1/kiosk/guest.py:14-45`
- 取号机请求模型：`app/schemas/kiosk.py:7-27`
- 取号机鉴权与风控：`app/services/kiosk/auth.py:30-99`
- 取号机签名实现：`app/services/kiosk/signing.py:5-41`
- 微信回调路由：`app/api/v1/portal/portal.py:167-200`
- 微信回调模型：`app/schemas/portal.py:37-42`
- 微信签名及状态规则：`app/services/wechat/service.py:18-77`
- 小程序兼容路由：`app/api/mini_program.py`
- 小程序 NCE 原样代理客户端：`app/services/mini_program/client.py`
- 风控错误语义：`app/services/risk_control/errors.py:1-34`
- NCE 内部 Protocol：`app/services/nce/client.py:10-156`
- 登机牌内部 Protocol：`app/services/boarding_pass/client.py:9-54`
- OCR 内部 Protocol：`app/services/passport/client.py:7-46`

## 19. 契约优先级

发生冲突时按以下顺序裁决：

1. 双方签字确认并版本化的正式接口契约；
2. 真实联调环境抓包和厂商官方文档；
3. 本文档中标记为已实现的当前代码行为；
4. 本文档中的设计基线；
5. Mock 行为。

任何“待确认”字段不得仅依据 Mock 推断为生产事实。接口变更必须同步更新本文档版本、自动化契约测试和脱敏报文样例。
