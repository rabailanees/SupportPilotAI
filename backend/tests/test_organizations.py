def test_create_organization(client):
    response = client.post(
        "/api/v1/organizations/",
        json={
            "name": "Test Organization",
            "slug": "test-organization",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Test Organization"
    assert data["slug"] == "test-organization"
    assert "id" in data


def test_list_organizations(client):
    client.post(
        "/api/v1/organizations/",
        json={
            "name": "First Organization",
            "slug": "first-organization",
        },
    )

    response = client.get("/api/v1/organizations/")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "first-organization"


def test_duplicate_organization_slug(client):
    payload = {
        "name": "First Organization",
        "slug": "duplicate-slug",
    }

    first_response = client.post(
        "/api/v1/organizations/",
        json=payload,
    )

    second_response = client.post(
        "/api/v1/organizations/",
        json={
            "name": "Another Organization",
            "slug": "duplicate-slug",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
