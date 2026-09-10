from pathlib import Path

from app.core.wifi_menu import WIFI_MENU_TREE


def test_wifi_menu_tree_has_unique_routes_and_existing_components() -> None:
    children = [child for catalog in WIFI_MENU_TREE for child in catalog["children"]]
    paths = [child["path"] for child in children]

    assert paths == [
        "/wifi/statistics",
        "/wifi/online-users",
        "/wifi/radius-logs",
        "/wifi/health",
        "/wifi/runtime-config",
    ]
    assert len(paths) == len(set(paths))
    for child in children:
        component = Path("web/src/views") / child["component"].lstrip("/") / "index.vue"
        assert component.exists(), component
