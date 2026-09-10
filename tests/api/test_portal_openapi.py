from app import app


def test_portal_openapi_contains_mock_authentication_contracts() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/portal/boarding-pass/verify" in paths
    assert "/api/v1/portal/passport/verify" in paths
    assert "/api/v1/portal/wechat/auth/start" in paths
    assert "/api/v1/portal/wechat/auth/callback" in paths
    assert "/api/v1/portal/wechat/auth/status" in paths
    passport_content = paths["/api/v1/portal/passport/verify"]["post"]["requestBody"]["content"]
    assert "image/jpeg" in passport_content
    assert "image/png" in passport_content
    assert "multipart/form-data" not in passport_content
