"""Tests pour l'endpoint MCP Checkout"""

import json
import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestMCPCheckout:
    """Tests pour le checkout MCP EU AI Act"""

    @patch("stripe.Customer.list")
    @patch("stripe.Customer.create")
    @patch("stripe.checkout.Session.create")
    def test_create_checkout_new_customer(self, mock_session_create, mock_customer_create, mock_customer_list):
        """Test création de checkout avec un nouveau client"""
        # Mock: aucun client existant
        mock_customer_list.return_value = Mock(data=[])

        # Mock: création d'un nouveau client
        mock_customer = Mock()
        mock_customer.id = "cus_test123"
        mock_customer_create.return_value = mock_customer

        # Mock: création de la session Stripe
        mock_session = Mock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/test123"
        mock_session_create.return_value = mock_session

        # Appel de l'endpoint
        response = client.post(
            "/api/checkout/mcp-eu-ai-act",
            json={
                "email": "test@example.com",
                "name": "Test User",
                "trial_days": 14
            }
        )

        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["checkout_url"] == "https://checkout.stripe.com/test123"
        assert data["session_id"] == "cs_test123"
        assert data["product"] == "MCP EU AI Act Compliance Monitoring"
        assert data["price"] == "9€/mois"
        assert data["trial_days"] == 14

        # Vérifier que le client a été créé
        mock_customer_create.assert_called_once()
        call_args = mock_customer_create.call_args[1]
        assert call_args["email"] == "test@example.com"
        assert call_args["name"] == "Test User"

    @patch("stripe.Customer.list")
    @patch("stripe.checkout.Session.create")
    def test_create_checkout_existing_customer(self, mock_session_create, mock_customer_list):
        """Test création de checkout avec un client existant"""
        # Mock: client existant
        mock_customer = Mock()
        mock_customer.id = "cus_existing123"
        mock_customer_list.return_value = Mock(data=[mock_customer])

        # Mock: création de la session Stripe
        mock_session = Mock()
        mock_session.id = "cs_test456"
        mock_session.url = "https://checkout.stripe.com/test456"
        mock_session_create.return_value = mock_session

        # Appel de l'endpoint
        response = client.post(
            "/api/checkout/mcp-eu-ai-act",
            json={
                "email": "existing@example.com",
                "trial_days": 14
            }
        )

        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["checkout_url"] == "https://checkout.stripe.com/test456"

        # Vérifier que le client existant a été utilisé
        session_call_args = mock_session_create.call_args[1]
        assert session_call_args["customer"] == "cus_existing123"

    def test_create_checkout_invalid_email(self):
        """Test avec un email invalide"""
        response = client.post(
            "/api/checkout/mcp-eu-ai-act",
            json={
                "email": "invalid-email",
                "trial_days": 14
            }
        )

        # Devrait échouer la validation
        assert response.status_code == 422

    @patch("stripe.Customer.list")
    @patch("stripe.Customer.create")
    @patch("stripe.checkout.Session.create")
    def test_create_checkout_with_promo_code(self, mock_session_create, mock_customer_create, mock_customer_list):
        """Test création de checkout avec code promo"""
        # Mock: aucun client existant
        mock_customer_list.return_value = Mock(data=[])

        # Mock: création d'un nouveau client
        mock_customer = Mock()
        mock_customer.id = "cus_test789"
        mock_customer_create.return_value = mock_customer

        # Mock: session Stripe
        mock_session = Mock()
        mock_session.id = "cs_test789"
        mock_session.url = "https://checkout.stripe.com/test789"
        mock_session_create.return_value = mock_session

        # Mock: code promo
        with patch("stripe.PromotionCode.list") as mock_promo_list:
            mock_promo = Mock()
            mock_promo.id = "promo_test123"
            mock_promo_list.return_value = Mock(data=[mock_promo])

            # Appel de l'endpoint avec code promo
            response = client.post(
                "/api/checkout/mcp-eu-ai-act",
                json={
                    "email": "promo@example.com",
                    "promotion_code": "LAUNCH50",
                    "trial_days": 14
                }
            )

            # Vérifications
            assert response.status_code == 200

    def test_get_mcp_info(self):
        """Test de l'endpoint d'information produit"""
        response = client.get("/api/checkout/mcp-eu-ai-act/info")

        assert response.status_code == 200
        data = response.json()
        assert data["product"] == "MCP EU AI Act Compliance Monitoring"
        assert data["price"]["amount"] == 9
        assert data["price"]["currency"] == "EUR"
        assert data["price"]["interval"] == "month"
        assert data["price"]["trial_days"] == 14
        assert len(data["features"]) > 0

    @patch("stripe.Customer.list")
    @patch("stripe.Customer.create")
    @patch("stripe.checkout.Session.create")
    def test_create_checkout_no_trial(self, mock_session_create, mock_customer_create, mock_customer_list):
        """Test création de checkout sans période d'essai"""
        # Mock: aucun client existant
        mock_customer_list.return_value = Mock(data=[])

        # Mock: création d'un nouveau client
        mock_customer = Mock()
        mock_customer.id = "cus_notrial"
        mock_customer_create.return_value = mock_customer

        # Mock: session Stripe
        mock_session = Mock()
        mock_session.id = "cs_notrial"
        mock_session.url = "https://checkout.stripe.com/notrial"
        mock_session_create.return_value = mock_session

        # Appel de l'endpoint sans trial
        response = client.post(
            "/api/checkout/mcp-eu-ai-act",
            json={
                "email": "notrial@example.com",
                "trial_days": 0
            }
        )

        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["trial_days"] == 0

        # Vérifier que la session n'a pas de trial
        session_call_args = mock_session_create.call_args[1]
        assert "subscription_data" not in session_call_args or session_call_args.get("subscription_data", {}).get("trial_period_days") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
