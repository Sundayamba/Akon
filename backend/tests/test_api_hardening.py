from fastapi.testclient import TestClient

from app.main import API_VERSION, app
from app.services.llm_provider import LLMProviderError
from tests.helpers import auth_headers


client = TestClient(app)


def test_root_returns_api_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["service"] == "akon-api"
    assert data["name"] == "Akon"
    assert data["version"] == API_VERSION
    assert data["environment"] == "development"
    assert data["status"] == "ok"


def test_version_returns_version_metadata() -> None:
    response = client.get("/version")

    assert response.status_code == 200

    data = response.json()

    assert data["service"] == "akon-api"
    assert data["version"] == API_VERSION
    assert data["environment"] == "development"


def test_request_id_header_is_added() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_existing_request_id_header_is_preserved() -> None:
    request_id = "test-request-id-123"

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": request_id,
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_unknown_route_uses_standard_error_shape() -> None:
    response = client.get("/unknown-route")

    assert response.status_code == 404

    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "http_error"
    assert data["error"]["status_code"] == 404
    assert "request_id" in data["error"]


def test_validation_error_uses_standard_error_shape() -> None:
    headers = auth_headers(client)

    response = client.post(
        "/chat/message",
        headers=headers,
        json={
            "message": "",
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "validation_error"
    assert data["error"]["status_code"] == 422
    assert data["error"]["message"] == "Request validation failed."
    assert "details" in data["error"]
    assert "request_id" in data["error"]


def test_ai_provider_failure_uses_standard_error_shape_and_does_not_commit(
    monkeypatch,
) -> None:
    headers = auth_headers(client)
    unique_message = "provider failure rollback probe 8b1d9d36"

    def raise_provider_error(*args, **kwargs) -> str:
        raise LLMProviderError("Simulated provider failure.")

    monkeypatch.setattr(
        "app.api.routes.chat.generate_akon_reply",
        raise_provider_error,
    )

    response = client.post(
        "/chat/message",
        headers=headers,
        json={
            "message": unique_message,
        },
    )

    assert response.status_code == 503

    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "http_error"
    assert data["error"]["status_code"] == 503
    assert data["error"]["message"] == (
        "Akon's AI provider is temporarily unavailable. "
        "Please try again shortly."
    )
    assert "request_id" in data["error"]

    conversations_response = client.get(
        "/chat/conversations",
        headers=headers,
    )

    assert conversations_response.status_code == 200

    conversations = conversations_response.json()

    assert all(
        conversation["title"] != unique_message
        for conversation in conversations
    )