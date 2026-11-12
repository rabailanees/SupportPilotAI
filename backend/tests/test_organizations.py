
def test_get_my_organization(client, tenant_context):
    response = client.get(
        "/api/v1/organizations/me",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(tenant_context["organization_a"].id)
    assert data["slug"] == "organization-a"


def test_user_cannot_access_another_organization(client, tenant_context):
    response = client.get(
        "/api/v1/organizations/me",
        headers=tenant_context["headers_b"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(
        tenant_context["organization_b"].id
    )


def test_organization_endpoint_requires_authentication(client):
    response = client.get("/api/v1/organizations/me")

    assert response.status_code == 401


def test_old_public_organization_list_endpoint_is_removed(client):
    response = client.get("/api/v1/organizations/")

    assert response.status_code == 404