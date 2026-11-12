def create_test_organization(client):
    response = client.post(
        "/api/v1/organizations/",
        json={
            "name": "Conversation Test Org",
            "slug": "conversation-test-org",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_test_conversation(client, organization_id):
    response = client.post(
        f"/api/v1/organizations/{organization_id}/conversations/",
        json={"customer_email": "customer@example.com"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_conversation(client):
    organization_id = create_test_organization(client)

    response = client.post(
        f"/api/v1/organizations/{organization_id}/conversations/",
        json={"customer_email": "customer@example.com"},
    )

    assert response.status_code == 201

    data = response.json()
    assert data["organization_id"] == organization_id
    assert data["customer_email"] == "customer@example.com"
    assert data["status"] == "open"
    assert "id" in data


def test_list_conversations(client):
    organization_id = create_test_organization(client)
    create_test_conversation(client, organization_id)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/conversations/"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["organization_id"] == organization_id


def test_create_conversation_for_unknown_organization(client):
    unknown_organization_id = "00000000-0000-0000-0000-000000000001"

    response = client.post(
        f"/api/v1/organizations/{unknown_organization_id}/conversations/",
        json={"customer_email": "customer@example.com"},
    )

    assert response.status_code == 404


def test_create_message(client):
    organization_id = create_test_organization(client)
    conversation_id = create_test_conversation(client, organization_id)

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/",
        json={
            "sender_type": "customer",
            "content": "I need help with my order.",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["conversation_id"] == conversation_id
    assert data["sender_type"] == "customer"
    assert data["content"] == "I need help with my order."
    assert "id" in data


def test_list_messages(client):
    organization_id = create_test_organization(client)
    conversation_id = create_test_conversation(client, organization_id)

    client.post(
        f"/api/v1/conversations/{conversation_id}/messages/",
        json={
            "sender_type": "customer",
            "content": "Hello, I need help.",
        },
    )

    response = client.get(
        f"/api/v1/conversations/{conversation_id}/messages/"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello, I need help."


def test_create_message_for_unknown_conversation(client):
    unknown_conversation_id = "00000000-0000-0000-0000-000000000002"

    response = client.post(
        f"/api/v1/conversations/{unknown_conversation_id}/messages/",
        json={
            "sender_type": "customer",
            "content": "Hello",
        },
    )

    assert response.status_code == 404


def test_create_message_with_invalid_sender_type(client):
    organization_id = create_test_organization(client)
    conversation_id = create_test_conversation(client, organization_id)

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/",
        json={
            "sender_type": "unknown",
            "content": "Hello",
        },
    )

    assert response.status_code == 422


def test_create_message_with_empty_content(client):
    organization_id = create_test_organization(client)
    conversation_id = create_test_conversation(client, organization_id)

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/",
        json={
            "sender_type": "customer",
            "content": "",
        },
    )

    assert response.status_code == 422
