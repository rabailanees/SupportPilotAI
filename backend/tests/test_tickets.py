def create_test_organization(client, name="Ticket Test Org", slug="ticket-test-org"):
    response = client.post(
        "/api/v1/organizations/",
        json={"name": name, "slug": slug},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_test_ticket(client, organization_id):
    response = client.post(
        f"/api/v1/organizations/{organization_id}/tickets/",
        json={
            "customer_email": "customer@example.com",
            "subject": "Order delivery issue",
            "description": "My order has not arrived yet.",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_ticket(client):
    organization_id = create_test_organization(client)

    response = client.post(
        f"/api/v1/organizations/{organization_id}/tickets/",
        json={
            "customer_email": "customer@example.com",
            "subject": "Order delivery issue",
            "description": "My order has not arrived yet.",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["organization_id"] == organization_id
    assert data["customer_email"] == "customer@example.com"
    assert data["subject"] == "Order delivery issue"
    assert data["status"] == "open"
    assert data["priority"] == "high"
    assert "id" in data


def test_list_tickets(client):
    organization_id = create_test_organization(client)
    create_test_ticket(client, organization_id)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/tickets/"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["organization_id"] == organization_id


def test_get_ticket(client):
    organization_id = create_test_organization(client)
    ticket_id = create_test_ticket(client, organization_id)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == ticket_id


def test_update_ticket_status(client):
    organization_id = create_test_organization(client)
    ticket_id = create_test_ticket(client, organization_id)

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket_id}",
        json={"status": "resolved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["priority"] == "high"


def test_update_ticket_priority(client):
    organization_id = create_test_organization(client)
    ticket_id = create_test_ticket(client, organization_id)

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket_id}",
        json={"priority": "urgent"},
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "urgent"


def test_update_ticket_with_invalid_status(client):
    organization_id = create_test_organization(client)
    ticket_id = create_test_ticket(client, organization_id)

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket_id}",
        json={"status": "cancelled"},
    )

    assert response.status_code == 422


def test_update_ticket_with_empty_payload(client):
    organization_id = create_test_organization(client)
    ticket_id = create_test_ticket(client, organization_id)

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket_id}",
        json={},
    )

    assert response.status_code == 400


def test_update_ticket_with_null_status(client):
    organization_id = create_test_organization(client)
    ticket_id = create_test_ticket(client, organization_id)

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket_id}",
        json={"status": None},
    )

    assert response.status_code == 422


def test_get_ticket_from_wrong_organization(client):
    organization_id = create_test_organization(client)
    ticket_id = create_test_ticket(client, organization_id)

    another_organization_id = create_test_organization(
        client,
        name="Another Organization",
        slug="another-organization",
    )

    response = client.get(
        f"/api/v1/organizations/{another_organization_id}/tickets/{ticket_id}"
    )

    assert response.status_code == 404
