"""Tests for billing endpoints and Stripe integration"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, "/opt/claude-ceo/workspace/arkwatch")

from src.api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_api_key():
    """Mock valid API key"""
    return "ak_test_valid_key_12345"


@pytest.fixture
def mock_user_data():
    """Mock user data"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "tier": "free",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "subscription_status": None,
    }


class TestBillingEndpointsAuth:
    """Test billing endpoints require authentication"""

    def test_subscription_requires_auth(self, client):
        """Test GET /billing/subscription requires API key"""
        response = client.get("/api/v1/billing/subscription")
        assert response.status_code == 401
        assert response.json()["detail"] == "API key required"

    def test_checkout_requires_auth(self, client):
        """Test POST /billing/checkout requires API key"""
        response = client.post("/api/v1/billing/checkout", json={"tier": "starter"})
        assert response.status_code == 401
        assert response.json()["detail"] == "API key required"

    def test_portal_requires_auth(self, client):
        """Test POST /billing/portal requires API key"""
        response = client.post("/api/v1/billing/portal")
        assert response.status_code == 401

    def test_cancel_requires_auth(self, client):
        """Test POST /billing/cancel requires API key"""
        response = client.post("/api/v1/billing/cancel")
        assert response.status_code == 401

    def test_usage_requires_auth(self, client):
        """Test GET /billing/usage requires API key"""
        response = client.get("/api/v1/billing/usage")
        assert response.status_code == 401


class TestBillingEndpointsWithAuth:
    """Test billing endpoints with valid authentication"""

    @patch("src.api.auth.validate_api_key")
    def test_subscription_free_user(self, mock_validate, client, mock_user_data):
        """Test subscription endpoint for free user"""
        mock_validate.return_value = mock_user_data
        response = client.get(
            "/api/v1/billing/subscription",
            headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "free"
        assert data["stripe_customer_id"] is None

    @patch("src.api.auth.validate_api_key")
    def test_checkout_invalid_tier(self, mock_validate, client, mock_user_data):
        """Test checkout with invalid tier"""
        mock_validate.return_value = mock_user_data
        response = client.post(
            "/api/v1/billing/checkout",
            headers={"X-API-Key": "test_key"},
            json={"tier": "invalid_tier"}
        )
        assert response.status_code == 400
        assert "Invalid tier" in response.json()["detail"]

    @patch("src.api.auth.validate_api_key")
    def test_portal_no_customer(self, mock_validate, client, mock_user_data):
        """Test portal creation without Stripe customer"""
        mock_validate.return_value = mock_user_data
        response = client.post(
            "/api/v1/billing/portal",
            headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 400
        assert "No billing account" in response.json()["detail"]

    @patch("src.api.auth.validate_api_key")
    def test_cancel_no_subscription(self, mock_validate, client, mock_user_data):
        """Test cancel without active subscription"""
        mock_validate.return_value = mock_user_data
        response = client.post(
            "/api/v1/billing/cancel",
            headers={"X-API-Key": "test_key"}
        )
        assert response.status_code == 400
        assert "No active subscription" in response.json()["detail"]


class TestStripeWebhooks:
    """Test Stripe webhook endpoint"""

    def test_webhook_missing_signature(self, client):
        """Test webhook rejects requests without signature"""
        response = client.post(
            "/api/v1/webhooks/stripe",
            content=b'{"type": "test"}'
        )
        assert response.status_code == 400
        assert "Missing Stripe signature" in response.json()["detail"]

    @patch("src.api.routers.webhooks.StripeService.construct_webhook_event")
    def test_webhook_invalid_payload(self, mock_construct, client):
        """Test webhook handles invalid payload"""
        mock_construct.side_effect = ValueError("Invalid payload")
        response = client.post(
            "/api/v1/webhooks/stripe",
            content=b'invalid',
            headers={"Stripe-Signature": "test_sig"}
        )
        assert response.status_code == 400
        assert "Invalid payload" in response.json()["detail"]

    @patch("src.api.routers.webhooks.StripeService.construct_webhook_event")
    @patch("src.api.routers.webhooks.get_user_by_customer_id")
    @patch("src.api.routers.webhooks.update_stripe_info")
    def test_webhook_checkout_completed(
        self, mock_update, mock_get_user, mock_construct, client
    ):
        """Test webhook handles checkout.session.completed"""
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                    "metadata": {"tier": "starter"}
                }
            }
        }
        mock_get_user.return_value = ("key_hash_123", {"email": "test@example.com"})

        response = client.post(
            "/api/v1/webhooks/stripe",
            content=b'{"type": "checkout.session.completed"}',
            headers={"Stripe-Signature": "test_sig"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_update.assert_called_once()

    @patch("src.api.routers.webhooks.StripeService.construct_webhook_event")
    @patch("src.api.routers.webhooks.get_user_by_customer_id")
    @patch("src.api.routers.webhooks.update_stripe_info")
    @patch("src.api.routers.webhooks.StripeService.get_tier_from_subscription")
    def test_webhook_subscription_deleted(
        self, mock_tier, mock_update, mock_get_user, mock_construct, client
    ):
        """Test webhook handles subscription.deleted (downgrade to free)"""
        mock_construct.return_value = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "canceled"
                }
            }
        }
        mock_get_user.return_value = ("key_hash_123", {"email": "test@example.com"})

        response = client.post(
            "/api/v1/webhooks/stripe",
            content=b'{"type": "customer.subscription.deleted"}',
            headers={"Stripe-Signature": "test_sig"}
        )

        assert response.status_code == 200
        mock_update.assert_called_with(
            "key_hash_123",
            subscription_id=None,
            subscription_status="canceled",
            tier="free"
        )


class TestStripeService:
    """Test StripeService methods"""

    def test_tier_prices_mapping(self):
        """Test tier to price mapping exists"""
        from src.billing.stripe_service import TIER_PRICES
        assert "starter" in TIER_PRICES
        assert "pro" in TIER_PRICES
        assert "business" in TIER_PRICES

    def test_get_tier_limits(self):
        """Test tier limits are defined"""
        from src.api.auth import get_tier_limits

        free_limits = get_tier_limits("free")
        assert free_limits["max_watches"] == 3

        starter_limits = get_tier_limits("starter")
        assert starter_limits["max_watches"] == 10

        pro_limits = get_tier_limits("pro")
        assert pro_limits["max_watches"] == 50

        business_limits = get_tier_limits("business")
        assert business_limits["max_watches"] == 1000
