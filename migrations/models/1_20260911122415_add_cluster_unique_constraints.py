from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `api` ADD UNIQUE INDEX `uid_api_method_7d43bb` (`method`, `path`);
        ALTER TABLE `deptclosure` ADD UNIQUE INDEX `uid_deptclosure_ancesto_ac5861` (`ancestor`, `descendant`);
        ALTER TABLE `menu` ADD UNIQUE INDEX `uid_menu_parent__73114c` (`parent_id`, `path`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `deptclosure` DROP INDEX `uid_deptclosure_ancesto_ac5861`;
        ALTER TABLE `menu` DROP INDEX `uid_menu_parent__73114c`;
        ALTER TABLE `api` DROP INDEX `uid_api_method_7d43bb`;"""
