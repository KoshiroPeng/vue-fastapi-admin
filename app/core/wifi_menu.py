from app.models.admin import Menu
from app.schemas.menus import MenuType

WIFI_MENU_TREE = [
    {
        "name": "WiFi运营",
        "path": "/wifi-operations",
        "icon": "ph:wifi-high-bold",
        "order": 10,
        "redirect": "/wifi/statistics",
        "children": [
            {
                "name": "认证统计",
                "path": "/wifi/statistics",
                "component": "/wifi/statistics",
                "icon": "ph:chart-line-up-bold",
                "order": 1,
            },
            {
                "name": "在线用户",
                "path": "/wifi/online-users",
                "component": "/wifi/online-users",
                "icon": "ph:devices-bold",
                "order": 2,
            },
        ],
    },
    {
        "name": "WiFi日志",
        "path": "/wifi-logs",
        "icon": "ph:list-magnifying-glass-bold",
        "order": 11,
        "redirect": "/wifi/radius-logs",
        "children": [
            {
                "name": "准入日志",
                "path": "/wifi/radius-logs",
                "component": "/wifi/radius-logs",
                "icon": "ph:clipboard-text-bold",
                "order": 1,
            }
        ],
    },
    {
        "name": "WiFi运维",
        "path": "/wifi-maintenance",
        "icon": "ph:activity-bold",
        "order": 12,
        "redirect": "/wifi/health",
        "children": [
            {
                "name": "外部服务状态",
                "path": "/wifi/health",
                "component": "/wifi/health",
                "icon": "ph:heartbeat-bold",
                "order": 1,
            },
            {
                "name": "运行配置摘要",
                "path": "/wifi/runtime-config",
                "component": "/wifi/runtime-config",
                "icon": "ph:sliders-horizontal-bold",
                "order": 2,
            },
        ],
    },
]


async def init_wifi_menus() -> list[Menu]:
    created_or_existing: list[Menu] = []
    for catalog in WIFI_MENU_TREE:
        parent, _ = await Menu.get_or_create(
            path=catalog["path"],
            parent_id=0,
            defaults={
                "menu_type": MenuType.CATALOG,
                "name": catalog["name"],
                "order": catalog["order"],
                "icon": catalog["icon"],
                "is_hidden": False,
                "component": "Layout",
                "keepalive": False,
                "redirect": catalog["redirect"],
            },
        )
        created_or_existing.append(parent)
        for child in catalog["children"]:
            item, _ = await Menu.get_or_create(
                path=child["path"],
                parent_id=parent.id,
                defaults={
                    "menu_type": MenuType.MENU,
                    "name": child["name"],
                    "order": child["order"],
                    "icon": child["icon"],
                    "is_hidden": False,
                    "component": child["component"],
                    "keepalive": False,
                    "redirect": "",
                },
            )
            created_or_existing.append(item)
    return created_or_existing
