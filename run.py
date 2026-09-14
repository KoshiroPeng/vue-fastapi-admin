import uvicorn
from uvicorn.config import LOGGING_CONFIG

from app.settings import settings

if __name__ == "__main__":
    # 修改默认日志配置
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    LOGGING_CONFIG["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=9999,
        reload=settings.DEBUG,
        log_config=LOGGING_CONFIG,
        access_log=False,
    )
