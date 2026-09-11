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
- Aerich
- SQLite 默认数据库
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

Docker 部署需要 Docker 17.05 或以上版本。

## 本地启动

### 启动后端

推荐使用 `uv` 管理后端依赖。

```powershell
pip install uv
uv venv
.\.venv\Scripts\activate
uv sync
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

## 初始化管理员

系统不再内置默认管理员密码。仅在用户表为空且明确配置以下环境变量时创建初始管理员：

```text
BOOTSTRAP_ADMIN_ENABLED=true
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_EMAIL=admin@example.invalid
BOOTSTRAP_ADMIN_PASSWORD=<至少 12 位的独立强密码>
```

管理员创建后应关闭 `BOOTSTRAP_ADMIN_ENABLED`，并通过受控 Secret 管理生产密码。已有数据库用户不受该开关影响。

## Docker 部署

镜像内会构建前端静态资源，通过 Nginx 提供页面，并把 `/api/` 请求转发给同一容器内的 FastAPI。Compose 会同时启动独立 Redis，并持久化 Redis、SQLite 和应用日志。

先在服务器创建 SQLite 文件和日志目录，并准备运行配置：

```bash
mkdir -p /srv/vue-fastapi-admin/data /srv/vue-fastapi-admin/logs /etc/vue-fastapi-admin
touch /srv/vue-fastapi-admin/data/db.sqlite3
cp deploy/.env.example /etc/vue-fastapi-admin/app.env
```

编辑 `/etc/vue-fastapi-admin/app.env`，至少设置部署环境、`SECRET_KEY`、CORS 来源、各业务密钥和初始管理员。配置文件不得放入镜像或提交到仓库。

可直接访问 Docker Hub 时执行：

```bash
docker compose -f deploy/compose.yaml up -d --build
```

使用华为云 SWR 镜像源时执行：

```bash
NODE_IMAGE=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:18-alpine \
PYTHON_IMAGE=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim \
REDIS_IMAGE=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/redis:7.2-alpine \
docker compose -f deploy/compose.yaml up -d --build
```

默认访问地址为 `http://服务器地址:18082`。可以通过 `APP_PORT` 调整宿主机端口。确认初始管理员创建成功后，应关闭 `BOOTSTRAP_ADMIN_ENABLED`、清除配置中的初始密码，并重新创建应用容器。

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
│   └── web.conf         Nginx 配置
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
- 本地 SQLite 数据库文件，例如 `db.sqlite3`
- Python 缓存目录，例如 `__pycache__/`
- 本地构建产物，例如前端 `dist/`
- 本地迁移生成目录，例如 `migrations/`

当前 `.gitignore` 已包含这些规则。

## 配置注意事项

- 后端默认使用 SQLite，数据库文件会在本地运行时生成。
- 后端服务默认端口为 `9999`。
- 前端开发服务默认端口为 `3100`。
- `APP_ENV=production` 时必须通过环境变量注入至少 32 字符的独立 `SECRET_KEY`。
- 生产环境禁止使用通配符 CORS 来源。
- 初始管理员创建默认关闭，启用时必须提供独立强密码。
