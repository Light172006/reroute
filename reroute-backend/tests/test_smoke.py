from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/docs")
    assert r.status_code == 200

def test_unauth_trips():
    r = client.get("/trips/")
    assert r.status_code in (401, 403)