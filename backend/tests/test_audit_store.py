"""Unit tests for Store, Concurrency, and PDF receipt per Section 5.12."""
import base64
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_checkout_and_pdf_receipt():
    client.post("/audit/v1/reset", json={"stock": {"var-jersey-001-M": 1, "var-jersey-001-L": 5}})

    resp = client.post("/audit/v1/checkout", json={
        "order_id": "ord-test-001",
        "customer_id": "cust-001",
        "items": [{"variant_id": "var-jersey-001-M", "quantity": 1}],
        "discount_code": "WELCOME10",
        "payment": {"token": "tok_success"},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "paid"
    assert data["discount_minor"] == 45000  # 10% of 450000
    assert data["total_minor"] == 405000

    # Verify receipt and PDF
    receipt = data["receipt"]
    assert "signature" in receipt
    pdf_bytes = base64.b64decode(receipt["pdf_base64"])
    assert pdf_bytes.startswith(b"%PDF")
    assert b"ord-test-001" in pdf_bytes

    # Second checkout on same variant should be OUT_OF_STOCK
    resp2 = client.post("/audit/v1/checkout", json={
        "order_id": "ord-test-002",
        "customer_id": "cust-002",
        "items": [{"variant_id": "var-jersey-001-M", "quantity": 1}],
        "discount_code": None,
        "payment": {"token": "tok_success"},
    })
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "OUT_OF_STOCK"


def test_payment_declined_releases_stock():
    client.post("/audit/v1/reset", json={"stock": {"var-jersey-001-M": 1}})

    resp = client.post("/audit/v1/checkout", json={
        "order_id": "ord-declined",
        "customer_id": "cust-001",
        "items": [{"variant_id": "var-jersey-001-M", "quantity": 1}],
        "discount_code": None,
        "payment": {"token": "tok_declined"},
    })
    assert resp.status_code == 402
    assert resp.json()["error"]["code"] == "PAYMENT_DECLINED"

    # Stock was released, so next attempt can succeed
    inv = client.get("/audit/v1/inventory/var-jersey-001-M").json()
    assert inv["stock"] == 1
