# vue-fastapi-admin

基于 FastAPI、Vue 3、Naive UI 的前后端分离后台管理系统。项目提供用户、角色、菜单、部门、API 权限和审计日志等基础管理能力，适合作为内部管理系统的基础工程。

当前仓库地址：

```text
https://github.com/KoshiroPeng/vue-fastapi-admin.git
```

## 项目文档

- [详细设计说明书](doc/深圳机场WiFi多方式认证系统详细设计说明书.md)
- [实施任务计划](doc/深圳机场WiFi多方式认证系统实施任务计划.md)
- [执行任务清单与进度](doc/深圳机场WiFi多方式认证系统任务清单.md)

后续开发开始、完成或阻塞任务时，应同步更新执行任务清单。

## 功能概览

- 用户管理：支持用户增删改查、重置密码、启用或停用用户。
- 角色管理：支持角色维护，并可按角色分配菜单和接口权限。
- 菜单管理：支持后台动态菜单和前端动态路由。
- 部门管理：支持组织部门维护。
- API 管理：支持扫描和维护后端接口权限。
- 审计日志：记录接口访问行为，便于追踪操作。
- 认证鉴权：使用 JWT 登录认证，并支持按钮级和接口级权限控制。

## 技术栈

后端：

- Python 3.11
- FastAPI
- Tortoise ORM
- MySQL 8.0
- Uvicorn

前端：

- Vue 3
- Vite
- Naive UI
- Pinia
- Vue Router
- Axios
- UnoCSS
- pnpm

## 环境要求

- Python 3.11 或以上版本
- Node.js 18.8.0 或以上版本
- pnpm
- Git
- MySQL 8.0

Docker 部署需要 Docker 17.05 或以上版本。

## 本地启动

### 启动后端

推荐使用 `uv` 管理后端依赖。

```powershell
pip install uv
uv venv
.\.venv\Scripts\activate
uv sync
Copy-Item deploy/.env.example .env
# 编辑 .env，配置 MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD 和 MYSQL_DATABASE
# 首次启动前在 MySQL 客户端中执行 deploy/init.sql
python run.py
```

后端默认监听：

```text
http://localhost:9999
```

接口文档地址：

```text
http://localhost:9999/docs
```

如果不用 `uv`，也可以使用 `pip` 安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python run.py
```

### 启动前端

```powershell
cd web
npm i -g pnpm
pnpm install
pnpm dev
```

前端默认端口来自前端环境配置，当前为：

```text
http://localhost:3100
```

开发环境中，前端会把 `/api/v1` 请求代理到后端服务。

## 服务器部署

现场部署使用宿主机安装的 MySQL、Redis 和 Nginx。Docker Compose 只运行两个 FastAPI 容器，分别映射到宿主机 `19001` 和 `19002`。Nginx 直接托管前端静态文件，并通过 upstream 将 API 请求分发到一台或多台服务器上的 FastAPI 实例。

### 准备配置

先安装 MySQL 8.0、Redis 7.x、Nginx 和 Docker，然后创建运行目录：

```bash
mkdir -p /srv/vue-fastapi-admin/logs/app /opt/vue-fastapi-admin/logs/nginx /etc/vue-fastapi-admin
cp deploy/.env.example /etc/vue-fastapi-admin/app.env
chown root:root /etc/vue-fastapi-admin/app.env
chmod 600 /etc/vue-fastapi-admin/app.env
```

先在 MySQL 中创建数据库和最小权限业务账号，再在 `/etc/vue-fastapi-admin/app.env` 中明文填写 MySQL、Redis、`SECRET_KEY`、CORS 来源和业务密钥。该文件只保存在服务器，不得提交到仓库。两台应用服务器必须连接同一套 MySQL 和 Redis。

第三方小程序继续使用既有契约：`POST /secoWS/service/NewGuestManagerServices` 原样转发 SOAP/XML，`GET /PortalServer/AppPortalAuth` 根据 `messageType=authRequest` 或 `messageType=syncPortalAuthResultRequest` 原样转发查询参数和 JSON 响应。上游地址分别由 `MINI_PROGRAM_GUEST_SERVICE_URL` 和 `MINI_PROGRAM_PORTAL_AUTH_URL` 配置。该链路与登机牌、护照使用的 JSON 访客创建适配器相互独立。

真实 NCE 北向客户端由 `NCE_MOCK_ENABLED=false` 启用。每个 FastAPI 进程维护一个长生命周期 HTTP 连接池和一个进程内 Token 缓存；登机牌或护照验证通过后，后端依次创建临时访客、提交 HACA 授权并轮询到明确成功，才向 Portal 返回 `networkAuthorized=true`。生产环境必须配置 `NCE_BASE_URL`、`NCE_USERNAME`、`NCE_PASSWORD`、`NCE_GUEST_USER_GROUP_ID`，并按现场情况配置 CA、HACA 策略及状态值映射。具体字段见[第三方接口对接文档](doc/深圳机场WiFi多方式认证系统第三方接口对接文档.md)。

`APP_BIND_IP=0.0.0.0` 允许另一台服务器上的 Nginx 访问后端端口。防火墙必须限制 `19001`、`19002` 只允许 Nginx 服务器访问。`APP_DOCKER_SUBNET` 必须与现场已有网段不冲突。

### 初始化数据库

首次部署时，使用 MySQL 管理账号在数据库服务器执行全量初始化 SQL：

```bash
mysql -u root -p < deploy/init.sql
```

`init.sql` 面向全新数据库，包含完整表结构、索引、菜单、API 权限、角色和初始管理员。初始账号为 `admin / 123456`，首次登录后必须立即修改密码。该脚本不会删除或覆盖已有表，不得在已经投入使用的数据库中重复执行。

### 启动后端

每台应用服务器执行：

```bash
docker compose --env-file /etc/vue-fastapi-admin/app.env -f deploy/compose.yaml \
  up -d --build app-1 app-2
```

使用华为云 SWR Python 镜像源时执行：

```bash
PYTHON_IMAGE=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim \
docker compose --env-file /etc/vue-fastapi-admin/app.env -f deploy/compose.yaml \
  up -d --build app-1 app-2
```

两个容器各运行一个 Uvicorn worker。修改副本数量时应增加明确的服务和端口映射，并重新核算 MySQL 最大连接数，不使用动态宿主机端口。

### 部署前端和 Nginx

在构建机编译前端，并将产物放到 Nginx 静态目录：

```bash
cd web
pnpm install --frozen-lockfile
pnpm build
test -s /opt/vue-fastapi-admin/web/dist/index.html
cd ..
```

编辑 `deploy/nginx.conf`：保留 Nginx 所在服务器的两个本地 upstream；取得第二台应用服务器 IP 后，替换 `SECOND_APP_SERVER_IP` 并取消对应两行注释。然后安装配置：

```bash
cp /usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf.bak
cp deploy/nginx.conf /usr/local/nginx/conf/nginx.conf
/usr/local/nginx/sbin/nginx -t
/usr/local/nginx/sbin/nginx -s reload
```

部署健康检查：

```bash
curl -fsS http://127.0.0.1:19001/health/ready
curl -fsS http://127.0.0.1:19002/health/ready
curl -fsS http://127.0.0.1/health/live
curl -fsS http://127.0.0.1/health/ready
docker compose --env-file /etc/vue-fastapi-admin/app.env -f deploy/compose.yaml ps -a
```

后两个地址分别检查 Nginx 进程和完整的 Nginx、FastAPI、MySQL、Redis 链路。应用日志按容器主机名写入 `/srv/vue-fastapi-admin/logs/app`，Nginx 日志使用宿主机 `/var/log/nginx`。

## 常用命令

后端常用命令：

```powershell
python run.py
ruff check ./app
black ./ --check
isort ./ --profile black --check
```

前端常用命令：

```powershell
cd web
pnpm dev
pnpm build
pnpm lint
```

## 项目结构

```text
├── app                  后端应用代码
│   ├── api              API 路由
│   ├── controllers      业务控制器
│   ├── core             应用核心能力，例如中间件、异常处理、通用 CRUD
│   ├── log              日志配置
│   ├── models           数据模型
│   ├── schemas          请求和响应数据结构
│   ├── settings         后端配置
│   └── utils            工具函数
├── deploy               部署配置
│   ├── .env.example     服务端运行配置模板（不含真实密钥）
│   ├── compose.yaml     Docker Compose 编排
│   ├── Dockerfile       应用镜像构建文件
│   ├── entrypoint.sh    容器启动脚本
│   ├── init.sql         MySQL 全量初始化脚本
│   └── nginx.conf       宿主机 Nginx 单文件站点配置
├── logs                 本地运行日志（日志文件不提交）
├── web                  前端应用代码
│   ├── build            Vite 构建配置
│   ├── public           前端公共资源
│   ├── settings         前端项目配置
│   └── src              前端源码
├── Makefile             后端开发辅助命令
├── pyproject.toml       后端项目和依赖配置
├── requirements.txt     后端 pip 依赖清单
└── uv.lock              后端 uv 锁定文件
```

## 提交规则

以下内容不应提交到 Git 仓库：

- Python 虚拟环境，例如 `.venv/`
- 前端依赖目录，例如 `node_modules/`
- 本地数据库备份文件
- Python 缓存目录，例如 `__pycache__/`
- 本地构建产物，例如前端 `dist/`

当前 `.gitignore` 已包含这些规则。

## 配置注意事项

- 后端使用 MySQL 8.0，连接信息由 `MYSQL_*` 环境变量注入。
- 数据库通过 `deploy/init.sql` 初始化；应用启动时只连接数据库，不创建表或基础数据。
- 后端服务默认端口为 `9999`。
- Compose 默认运行两个独立后端容器，宿主机端口默认为 `19001` 和 `19002`。
- `APP_DOCKER_SUBNET` 必须与现场网段不冲突；`TRUSTED_PROXY_IPS` 必须包含本机 Docker 网关和 Nginx 主机地址。
- MySQL、Redis、Nginx 均由宿主机运维，不属于 Docker Compose 服务。
- 前端开发服务默认端口为 `3100`。
- `APP_ENV=production` 时必须通过环境变量注入至少 32 字符的独立 `SECRET_KEY`。
- 生产环境禁止使用通配符 CORS 来源。
- 全量 SQL 中的初始管理员密码只用于首次登录，部署后必须立即修改。
