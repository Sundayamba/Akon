from fastapi.testclient import TestClient


def register_user(
    client: TestClient,
    *,
    email: str = "rex@example.com",
    password: str = "strongpassword123",
    display_name: str = "Rex",
) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
        },
    )

    assert response.status_code == 201

    return response.json()


def login_user(
    client: TestClient,
    *,
    email: str = "rex@example.com",
    password: str = "strongpassword123",
) -> dict:
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()


def auth_headers(
    client: TestClient,
    *,
    email: str = "rex@example.com",
    password: str = "strongpassword123",
    display_name: str = "Rex",
) -> dict[str, str]:
    register_user(
        client,
        email=email,
        password=password,
        display_name=display_name,
    )

    login_response = login_user(
        client,
        email=email,
        password=password,
    )

    token = login_response["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }