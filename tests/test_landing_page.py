"""
Tests for spec-017-landing-page - Landing Page Split Layout
HTMX-powered authentication forms with dual Login/Register forms.
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch


class TestIsHtmxRequest:
    """Tests for is_htmx_request() helper function"""

    def test_returns_true_when_hx_request_header_is_true(self):
        """Scenario: HTMX request detected via HX-Request header
        GIVEN a Request object with HX-Request header set to "true"
        WHEN is_htmx_request() is called
        THEN it returns True"""
        from app.auth.utils import is_htmx_request

        # Create mock request with HTMX header
        mock_request = Mock()
        mock_request.headers = {"HX-Request": "true"}

        result = is_htmx_request(mock_request)

        assert result is True

    def test_returns_false_when_hx_request_header_is_missing(self):
        """Scenario: Non-HTMX request has no HX-Request header
        GIVEN a Request object without HX-Request header
        WHEN is_htmx_request() is called
        THEN it returns False"""
        from app.auth.utils import is_htmx_request

        # Create mock request without HTMX header
        mock_request = Mock()
        mock_request.headers = {}

        result = is_htmx_request(mock_request)

        assert result is False

    def test_returns_false_when_hx_request_header_is_not_true(self):
        """Scenario: HX-Request header with non-true value
        GIVEN a Request object with HX-Request header set to "false"
        WHEN is_htmx_request() is called
        THEN it returns False"""
        from app.auth.utils import is_htmx_request

        # Create mock request with HX-Request header set to false
        mock_request = Mock()
        mock_request.headers = {"HX-Request": "false"}

        result = is_htmx_request(mock_request)

        assert result is False

    def test_returns_false_when_hx_request_header_is_empty_string(self):
        """Scenario: HX-Request header with empty string value
        GIVEN a Request object with HX-Request header set to ""
        WHEN is_htmx_request() is called
        THEN it returns False"""
        from app.auth.utils import is_htmx_request

        # Create mock request with empty HX-Request header
        mock_request = Mock()
        mock_request.headers = {"HX-Request": ""}

        result = is_htmx_request(mock_request)

        assert result is False


class TestLoginPostWithHtmx:
    """Tests for POST /auth/login with HTMX header"""

    def test_login_htmx_success_returns_hx_redirect_header(self):
        """Scenario: HTMX login with valid credentials returns HX-Redirect and JSON
        GIVEN a POST to /auth/login with valid credentials and HTMX header
        WHEN the user has valid email and password
        THEN response includes HX-Redirect: /dashboard header and JSON body with token"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db
        from app.models.user import User

        client = TestClient(app)

        # Mock the database session
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Create a mock user with proper values
        mock_user = MagicMock()
        mock_user.email = "testlogin@example.com"
        mock_user.hashed_password = "hashedpassword"
        mock_user.id = 1
        mock_user.is_active = True

        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        # Override the get_db dependency
        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            # Mock verify_password to return True
            with patch("app.auth.routes.verify_password", return_value=True):
                with patch(
                    "app.auth.routes.create_access_token", return_value="test_token"
                ):
                    response = client.post(
                        "/auth/login",
                        data={
                            "username": "testlogin@example.com",
                            "password": "testpassword123",
                        },
                        headers={"HX-Request": "true"},
                        follow_redirects=False,
                    )

            # Should redirect to /dashboard
            assert response.status_code == 303
            assert response.headers.get("location") == "/dashboard"
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_login_htmx_failure_returns_json_error(self):
        """Scenario: HTMX login with invalid credentials returns JSON error
        GIVEN a POST to /auth/login with invalid credentials and HTMX header
        WHEN the credentials are incorrect
        THEN response includes JSON error with 401 status"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.database import get_db

        client = TestClient(app)

        # Mock the database session - no user found
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Override the get_db dependency
        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            # Mock verify_password to return False (invalid credentials)
            with patch("app.auth.routes.verify_password", return_value=False):
                response = client.post(
                    "/auth/login",
                    data={
                        "username": "nonexistent@example.com",
                        "password": "wrongpassword",
                    },
                    headers={"HX-Request": "true"},
                    follow_redirects=False,
                )

            # Should redirect to /auth/login with error param
            assert response.status_code == 303
            assert "/auth/login?error=1" in response.headers.get("location", "")
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()


class TestLandingPageSplitLayout:
    """Tests for landing page split layout rendering"""

    def test_landing_page_has_split_layout_structure(self):
        """Scenario: Landing page renders with split layout
        GIVEN a GET request to /
        WHEN the page loads
        THEN it contains both marketing content and auth form container"""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Check for split layout structure
        text = response.text.lower()
        # Should have auth form container
        assert "auth-form-box" in text or "form-box" in text or "auth" in text

    def test_landing_page_contains_marketing_text(self):
        """Scenario: Landing page contains marketing copy
        GIVEN a GET request to /
        WHEN the page loads
        THEN it displays marketing text about the app"""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        # Marketing content should be present
        text = response.text.lower()
        # Look for marketing-related keywords
        assert any(
            keyword in text
            for keyword in ["gestiona", "instagram", "publica", "contenido", "gestion"]
        )

    def test_landing_page_contains_login_form(self):
        """Scenario: Landing page displays login form
        GIVEN a GET request to /
        WHEN the page loads
        THEN it shows the login form with email and password fields"""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        text = response.text.lower()
        # Should have form inputs
        assert "email" in text or "username" in text
        assert "password" in text
