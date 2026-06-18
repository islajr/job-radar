import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from backend.config import settings

# Prevent database connection attempts on lifespan startup
@pytest.fixture(autouse=True)
def mock_db_init():
    with patch("backend.database.init_db", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def client():
    # Override settings.database_url and database dependency to avoid hitting postgres
    from backend.database import get_db
    from backend.main import app

    async def override_get_db():
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        async def mock_refresh(instance):
            import uuid
            if getattr(instance, "id", None) is None:
                instance.id = uuid.uuid4()
            if getattr(instance, "is_admin", None) is None:
                instance.is_admin = False

        db.refresh = mock_refresh
        yield db

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()

def test_whitelist_validation(client):
    """
    Test that registration allows whitelisted emails, rejects non-whitelisted emails,
    and allows everything if the whitelist configuration is empty.
    """
    # Case 1: Whitelist is configured
    settings.signup_whitelist = "allowed1@example.com, allowed2@example.com"

    # Register with allowed email
    response = client.post("/api/auth/register", json={
        "email": "allowed1@example.com",
        "password": "securepassword123",
        "full_name": "Allowed One"
    })
    # Mock database is used, registration should succeed (returns 200)
    assert response.status_code == 200
    assert response.json()["email"] == "allowed1@example.com"

    # Register with non-whitelisted email
    response = client.post("/api/auth/register", json={
        "email": "uninvited@example.com",
        "password": "securepassword123",
        "full_name": "Uninvited"
    })
    assert response.status_code == 403
    assert response.json()["detail"] == "Registration is restricted to whitelisted email addresses."

    # Register with allowed email (different casing)
    response = client.post("/api/auth/register", json={
        "email": "ALLOWED2@EXAMPLE.COM",
        "password": "securepassword123",
        "full_name": "Allowed Two"
    })
    assert response.status_code == 200
    assert response.json()["email"].lower() == "allowed2@example.com"

    # Case 2: Whitelist is empty (anyone can register)
    settings.signup_whitelist = ""

    response = client.post("/api/auth/register", json={
        "email": "uninvited@example.com",
        "password": "securepassword123",
        "full_name": "Uninvited"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "uninvited@example.com"


def test_rate_limiting_middleware(client):
    """
    Test that RateLimitMiddleware restricts anonymous visitors to 15 requests/min on API routes,
    supports X-Forwarded-For IP extraction, and bypasses signed-in sessions.
    """
    from backend.main import app
    # Get access to the middleware instance to reset/manipulate history if needed
    middleware_instance = None
    for m in app.user_middleware:
        if m.cls.__name__ == "RateLimitMiddleware":
            # However, Starlette adds middleware dynamically. 
            # We can also just mock time.time or test rate limiting using sequential requests.
            pass

    # We will mock time.time to control sliding window behavior
    with patch("time.time") as mock_time:
        mock_time.return_value = 1000.0

        headers_client1 = {"X-Forwarded-For": "1.1.1.1"}
        headers_client2 = {"X-Forwarded-For": "2.2.2.2"}

        # Client 1 makes 15 requests to /api/auth/login (bad payload to avoid DB but hit endpoint)
        for _ in range(15):
            response = client.post("/api/auth/login", json={}, headers=headers_client1)
            # Response should be 422 (validation error on payload) or 401, not 429
            assert response.status_code != 429

        # Client 1 makes 16th request -> should get 429
        response = client.post("/api/auth/login", json={}, headers=headers_client1)
        assert response.status_code == 429
        assert "Too Many Requests" in response.json()["detail"]

        # Client 2 makes a request with different IP -> should succeed (not 429)
        response = client.post("/api/auth/login", json={}, headers=headers_client2)
        assert response.status_code != 429

        # Advance time by 61 seconds for Client 1 -> should succeed again
        mock_time.return_value = 1061.0
        response = client.post("/api/auth/login", json={}, headers=headers_client1)
        assert response.status_code != 429

        # Make another 14 requests (total 15 in the new window)
        for _ in range(14):
            response = client.post("/api/auth/login", json={}, headers=headers_client1)
            assert response.status_code != 429
        
        # 16th request in new window -> should get 429
        response = client.post("/api/auth/login", json={}, headers=headers_client1)
        assert response.status_code == 429


def test_rate_limit_bypass_for_sessions(client):
    """
    Test that users with a session cookie bypass rate-limiting completely.
    """
    with patch("time.time") as mock_time:
        mock_time.return_value = 2000.0

        headers = {"X-Forwarded-For": "3.3.3.3"}
        cookies = {"session": "dummy-session-token"}

        # Make 20 requests using session cookie
        for _ in range(20):
            response = client.post("/api/auth/login", json={}, headers=headers, cookies=cookies)
            # Since a session cookie is present, it should bypass the rate limiter middleware
            # and hit the login route validator, returning 422 Unprocessable Entity, not 429.
            assert response.status_code != 429
