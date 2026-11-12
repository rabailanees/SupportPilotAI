from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def registration_payload(
    email="new-admin@example.com",
    slug="new-test-organization",
):
    return {
        "organization_name": "New Test Organization",
        "organization_slug": slug,
        "email": email,
        "password": "StrongPassword123!",
    }


def test_register_creates_organization_and_admin(client):
    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(),
    )

    assert response.status_code == 201

    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "new-admin@example.com"
    assert data["user"]["role"] == "admin"
    assert data["user"]["is_active"] is True
    assert data["user"]["organization_id"]


def test_register_rejects_duplicate_organization_slug(client):
    first = client.post(
        "/api/v1/auth/register",
        json=registration_payload(),
    )

    second = client.post(
        "/api/v1/auth/register",
        json=registration_payload(
            email="another-admin@example.com",
        ),
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_register_rejects_short_password(client):
    payload = registration_payload()
    payload["password"] = "short"

    response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert response.status_code == 422


def test_login_with_valid_credentials(client):
    client.post(
        "/api/v1/auth/register",
        json=registration_payload(),
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "new-admin@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["user"]["email"] == "new-admin@example.com"


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json=registration_payload(),
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "new-admin@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401


def test_protected_endpoint_rejects_expired_token(
    client,
    tenant_context,
):
    expired_payload = {
        "sub": str(tenant_context["user_a"].id),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "type": "access",
    }

    expired_token = jwt.encode(
        expired_payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401

def test_protected_endpoint_rejects_inactive_user(client, tenant_context, db_session):
    user = tenant_context["user_a"]
    user.is_active = False
    db_session.commit()

    response = client.get(
        "/api/v1/organizations/me",
        headers=tenant_context["headers_a"],
    )

    assert response.status_code == 401


def test_protected_endpoint_rejects_wrong_token_type(client, tenant_context):
    payload = {
        "sub": str(tenant_context["user_a"].id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "type": "refresh",
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_protected_endpoint_rejects_forged_signature(client, tenant_context):
    payload = {
        "sub": str(tenant_context["user_a"].id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "type": "access",
    }

    forged_token = jwt.encode(
        payload,
        "forged-signature-test-key-not-the-real-secret-2026",
        algorithm=settings.ALGORITHM,
    )

    response = client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )

    assert response.status_code == 401
