from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID
from app.log import logger
from app.models import Role, User
from app.settings import settings


class AuthControl:
    @classmethod
    async def is_authed(cls, token: str = Header(..., description="token验证")) -> Optional["User"]:
        try:
            decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = decode_data.get("user_id")
            if not isinstance(user_id, int):
                raise HTTPException(status_code=401, detail="无效的Token")
            user = await User.filter(id=user_id).first()
            if not user or not user.is_active:
                raise HTTPException(status_code=401, detail="认证失败")
            CTX_USER_ID.set(user_id)
            return user
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status_code=401, detail="登录已过期") from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail="无效的Token") from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("event=authentication_backend_failed")
            raise HTTPException(status_code=500, detail="认证服务暂不可用") from exc


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        if current_user.is_superuser:
            return
        method = request.method
        path = request.url.path
        roles: list[Role] = await current_user.roles
        if not roles:
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        apis = [await role.apis for role in roles]
        permission_apis = list(set((api.method, api.path) for api in sum(apis, [])))
        # path = "/api/v1/auth/userinfo"
        # method = "GET"
        if (method, path) not in permission_apis:
            raise HTTPException(status_code=403, detail=f"Permission denied method:{method} path:{path}")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)
