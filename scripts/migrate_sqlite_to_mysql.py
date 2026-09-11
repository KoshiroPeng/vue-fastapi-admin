import argparse
import asyncio
import sqlite3
from pathlib import Path

import asyncmy

from app.settings import settings


TABLES = (
    "api",
    "auditlog",
    "dept",
    "deptclosure",
    "menu",
    "role",
    "user",
    "wifi_external_call_log",
    "role_api",
    "role_menu",
    "user_role",
)


def snapshot_sqlite(source_path: Path) -> sqlite3.Connection:
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite 文件不存在: {source_path}")

    source = sqlite3.connect(f"file:{source_path.resolve()}?mode=ro", uri=True)
    snapshot = sqlite3.connect(":memory:")
    try:
        source.backup(snapshot)
    finally:
        source.close()
    snapshot.row_factory = sqlite3.Row
    return snapshot


async def ensure_empty_target(cursor: asyncmy.cursors.Cursor, replace: bool) -> None:
    populated = []
    for table in TABLES:
        await cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = (await cursor.fetchone())[0]
        if count:
            populated.append(f"{table}={count}")

    if populated and not replace:
        raise RuntimeError("MySQL 目标表不是空表，拒绝覆盖: " + ", ".join(populated))

    if replace:
        await cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in reversed(TABLES):
            await cursor.execute(f"DELETE FROM `{table}`")
        await cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


async def copy_table(
    source: sqlite3.Connection,
    cursor: asyncmy.cursors.Cursor,
    table: str,
) -> int:
    rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
    if not rows:
        return 0

    columns = rows[0].keys()
    column_sql = ", ".join(f"`{column}`" for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    values = [tuple(row[column] for column in columns) for row in rows]
    await cursor.executemany(
        f"INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})",
        values,
    )
    return len(values)


async def migrate(source_path: Path, replace: bool) -> None:
    if not settings.MYSQL_PASSWORD:
        raise RuntimeError("MYSQL_PASSWORD 未配置")

    source = snapshot_sqlite(source_path)
    connection = await asyncmy.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD.get_secret_value(),
        database=settings.MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=False,
        connect_timeout=settings.MYSQL_CONNECT_TIMEOUT_SECONDS,
    )
    try:
        async with connection.cursor() as cursor:
            await ensure_empty_target(cursor, replace)
            for table in TABLES:
                source_count = await copy_table(source, cursor, table)
                await cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                target_count = (await cursor.fetchone())[0]
                if target_count != source_count:
                    raise RuntimeError(f"表 {table} 数量不一致: SQLite={source_count}, MySQL={target_count}")
                print(f"{table}: {target_count}")
        await connection.commit()
    except Exception:
        await connection.rollback()
        raise
    finally:
        source.close()
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将现有 SQLite 数据一次性迁移到已建表的 MySQL 数据库")
    parser.add_argument("--source", type=Path, default=Path("db.sqlite3"), help="SQLite 数据库文件")
    parser.add_argument("--replace", action="store_true", help="清空 MySQL 业务表后重新导入")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(migrate(arguments.source, arguments.replace))
