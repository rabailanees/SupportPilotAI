def create_conversation(client, organization_id, headers, email="customer@example.com"):
    response = client.post(
        f"/api/v1/organizations/{organization_id}/conversations/",
        json={"customer_email": email},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_message(client, conversation_id, headers, content="Hello"):
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/",
        json={
            "sender_type": "customer",
            "content": content,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_conversation(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)

    data = create_conversation(
        client,
        organization_id,
        tenant_context["headers_a"],
    )

    assert data["organization_id"] == organization_id
    assert data["customer_email"] == "customer@example.com"
    assert data["status"] == "open"
    assert data["id"]


def test_list_conversations(client, tenant_context):
    organization_id = str(tenant_context["organization_a"].id)

    create_conversation(
        client,
        organization_id,
        tenant_context["headers_a"],
    )

    response = client.get(
        f"/api/v1/organizations/{organization_id}/conversations/",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["organization_id"] == organization_id


def test_conversation_creation_ignores_spoofed_organization_id(
    client,
    tenant_context,
):
    organization_a_id = str(tenant_context["organization_a"].id)
    organization_b_id = str(tenant_context["organization_b"].id)

    response = client.post(
        f"/api/v1/organizations/{organization_a_id}/conversations/",
        json={
            "customer_email": "customer@example.com",
            "organization_id": organization_b_id,
        },
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 201
    assert response.json()["organization_id"] == organization_a_id


def test_user_cannot_create_conversation_for_another_organization(
    client,
    tenant_context,
):
    organization_b_id = str(tenant_context["organization_b"].id)

    response = client.post(
        f"/api/v1/organizations/{organization_b_id}/conversations/",
        json={"customer_email": "customer@example.com"},
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_user_cannot_list_another_organizations_conversations(
    client,
    tenant_context,
):
    organization_b_id = str(tenant_context["organization_b"].id)

    create_conversation(
        client,
        organization_b_id,
        tenant_context["headers_b"],
    )

    response = client.get(
        f"/api/v1/organizations/{organization_b_id}/conversations/",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_create_message(client, tenant_context):
    organization_a_id = str(tenant_context["organization_a"].id)

    conversation = create_conversation(
        client,
        organization_a_id,
        tenant_context["headers_a"],
    )

    message = create_message(
        client,
        conversation["id"],
        tenant_context["headers_a"],
        "I need help with my order.",
    )

    assert message["conversation_id"] == conversation["id"]
    assert message["sender_type"] == "customer"
    assert message["content"] == "I need help with my order."


def test_list_messages(client, tenant_context):
    organization_a_id = str(tenant_context["organization_a"].id)

    conversation = create_conversation(
        client,
        organization_a_id,
        tenant_context["headers_a"],
    )

    create_message(
        client,
        conversation["id"],
        tenant_context["headers_a"],
        "Hello, I need help.",
    )

    response = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages/",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello, I need help."


def test_user_cannot_read_another_organizations_messages(
    client,
    tenant_context,
):
    organization_b_id = str(tenant_context["organization_b"].id)

    conversation = create_conversation(
        client,
        organization_b_id,
        tenant_context["headers_b"],
    )

    create_message(
        client,
        conversation["id"],
        tenant_context["headers_b"],
    )

    response = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages/",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_user_cannot_create_message_in_another_organizations_conversation(
    client,
    tenant_context,
):
    organization_b_id = str(tenant_context["organization_b"].id)

    conversation = create_conversation(
        client,
        organization_b_id,
        tenant_context["headers_b"],
    )

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages/",
        json={
            "sender_type": "customer",
            "content": "Unauthorized message",
        },
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_create_message_for_unknown_conversation(client, tenant_context):
    unknown_conversation_id = "00000000-0000-0000-0000-000000000002"

    response = client.post(
        f"/api/v1/conversations/{unknown_conversation_id}/messages/",
        json={
            "sender_type": "customer",
            "content": "Hello",
        },
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 404


def test_create_conversation_requires_authentication(client):
    response = client.post(
        "/api/v1/organizations/00000000-0000-0000-0000-000000000001/conversations/",
        json={"customer_email": "customer@example.com"},
    )

    assert response.status_code == 401


def test_create_message_requires_authentication(client):
    response = client.post(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000002/messages/",
        json={
            "sender_type": "customer",
            "content": "Hello",
        },
    )

    assert response.status_code == 401


def test_create_message_with_invalid_sender_type(client, tenant_context):
    organization_a_id = str(tenant_context["organization_a"].id)

    conversation = create_conversation(
        client,
        organization_a_id,
        tenant_context["headers_a"],
    )

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages/",
        json={
            "sender_type": "unknown",
            "content": "Hello",
        },
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 422


def test_create_message_with_empty_content(client, tenant_context):
    organization_a_id = str(tenant_context["organization_a"].id)

    conversation = create_conversation(
        client,
        organization_a_id,
        tenant_context["headers_a"],
    )

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages/",
        json={
            "sender_type": "customer",
            "content": "",
        },
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 422
