from fastapi.testclient import TestClient
from app.main import create_app
from app.providers.mock import MockMarketDataProvider

def test_health():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"

def test_market_overview():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/market/overview")
    assert response.status_code == 200

def test_get_nifty():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/market/nifty")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "NIFTY"

def test_get_banknifty():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/market/banknifty")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BANKNIFTY"

def test_get_sensex():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/market/sensex")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SENSEX"

def test_get_vix():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/market/vix")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "INDIA VIX"

def test_mock_provider():
    provider = MockMarketDataProvider()
    assert provider.is_connected() is True
    nifty = provider.get_quote("NIFTY")
    assert nifty is not None
    assert nifty.price > 0