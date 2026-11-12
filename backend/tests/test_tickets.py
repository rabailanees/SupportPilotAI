def create_test_ticket(client, organization_id, headers, conversation_id=None):
    payload = {
        "customer_email": "customer@example.com",
        "subject": "Order delivery issue",
        "description": "My order has not arrived yet.",
        "priority": "high",
    }
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    response = client.post(
        f"/api/v1/organizations/{organization_id}/tickets/",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_ticket(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)

    data = create_test_ticket(
        client, organization_id, tenant_context["headers_a"]
    )

    assert data["organization_id"] == organization_id
    assert data["customer_email"] == "customer@example.com"
    assert data["subject"] == "Order delivery issue"
    assert data["status"] == "open"
    assert data["priority"] == "high"
    assert data["id"]


def test_list_tickets(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)
    create_test_ticket(client, organization_id, tenant_context["headers_a"])

    response = client.get(
        f"/api/v1/organizations/{organization_id}/tickets/",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["organization_id"] == organization_id


def test_get_ticket(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)
    ticket = create_test_ticket(
        client, organization_id, tenant_context["headers_a"]
    )

    response = client.get(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket['id']}",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == ticket["id"]


def test_update_ticket_status(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)
    ticket = create_test_ticket(
        client, organization_id, tenant_context["headers_a"]
    )

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket['id']}",
        json={"status": "resolved"},
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["priority"] == "high"


def test_update_ticket_priority(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)
    ticket = create_test_ticket(
        client, organization_id, tenant_context["headers_a"]
    )

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket['id']}",
        json={"priority": "urgent"},
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "urgent"


def test_update_ticket_with_invalid_status(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)
    ticket = create_test_ticket(
        client, organization_id, tenant_context["headers_a"]
    )

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket['id']}",
        json={"status": "cancelled"},
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 422


def test_update_ticket_with_empty_payload(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)
    ticket = create_test_ticket(
        client, organization_id, tenant_context["headers_a"]
    )

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket['id']}",
        json={},
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 400


def test_update_ticket_with_null_status(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)
    ticket = create_test_ticket(
        client, organization_id, tenant_context["headers_a"]
    )

    response = client.patch(
        f"/api/v1/organizations/{organization_id}/tickets/{ticket['id']}",
        json={"status": None},
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 422


def test_user_cannot_access_another_organizations_ticket(client, tenant_context):
    organization_b_id = str(tenant_context["organization_b"].id)
    ticket = create_test_ticket(
        client, organization_b_id, tenant_context["headers_b"]
    )

    response = client.get(
        f"/api/v1/organizations/{organization_b_id}/tickets/{ticket['id']}",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_user_cannot_list_another_organizations_tickets(client, tenant_context):
    organization_b_id = str(tenant_context["organization_b"].id)
    create_test_ticket(client, organization_b_id, tenant_context["headers_b"])

    response = client.get(
        f"/api/v1/organizations/{organization_b_id}/tickets/",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_user_cannot_update_another_organizations_ticket(client, tenant_context):
    organization_b_id = str(tenant_context["organization_b"].id)
    ticket = create_test_ticket(
        client, organization_b_id, tenant_context["headers_b"]
    )

    response = client.patch(
        f"/api/v1/organizations/{organization_b_id}/tickets/{ticket['id']}",
        json={"status": "resolved"},
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_user_cannot_create_ticket_for_another_organization(client, tenant_context):
    organization_b_id = str(tenant_context["organization_b"].id)

    response = client.post(
        f"/api/v1/organizations/{organization_b_id}/tickets/",
        json={
            "customer_email": "customer@example.com",
            "subject": "Unauthorized ticket",
            "description": "This should not be created.",
            "priority": "high",
        },
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_ticket_creation_ignores_spoofed_organization_id(client, tenant_context):
    organization_a_id = str(tenant_context["organization_a"].id)
    organization_b_id = str(tenant_context["organization_b"].id)

    response = client.post(
        f"/api/v1/organizations/{organization_a_id}/tickets/",
        json={
            "customer_email": "customer@example.com",
            "subject": "Tenant isolation test",
            "description": "Testing organization ownership.",
            "priority": "high",
            "organization_id": organization_b_id,
        },
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 201, response.text
    assert response.json()["organization_id"] == organization_a_id


def test_user_cannot_attach_another_organizations_conversation(client, tenant_context):
    organization_b_id = str(tenant_context["organization_b"].id)

    conversation_response = client.post(
        f"/api/v1/organizations/{organization_b_id}/conversations/",
        json={"customer_email": "customer@example.com"},
        headers=tenant_context["headers_b"],
    )
    assert conversation_response.status_code == 201, conversation_response.text
    conversation_id = conversation_response.json()["id"]

    organization_a_id = str(tenant_context["organization_a"].id)
    response = client.post(
        f"/api/v1/organizations/{organization_a_id}/tickets/",
        json={
            "customer_email": "customer@example.com",
            "subject": "Cross-tenant conversation test",
            "description": "This must not be attached.",
            "priority": "high",
            "conversation_id": conversation_id,
        },
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_create_ticket_requires_authentication(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)

    response = client.post(
        f"/api/v1/organizations/{organization_id}/tickets/",
        json={
            "customer_email": "customer@example.com",
            "subject": "Unauthenticated ticket",
            "description": "This should be rejected.",
            "priority": "high",
        },
    )

    assert response.status_code == 401


def test_list_tickets_requires_authentication(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/tickets/"
    )

    assert response.status_code == 401


def test_get_unknown_ticket(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)
    unknown_ticket_id = "00000000-0000-0000-0000-000000000002"

    response = client.get(
        f"/api/v1/organizations/{organization_id}/tickets/{unknown_ticket_id}",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404
