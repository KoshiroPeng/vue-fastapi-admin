import asyncio

from tortoise import Tortoise

from app.core.init_app import init_data


async def main() -> None:
    try:
        await init_data()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
