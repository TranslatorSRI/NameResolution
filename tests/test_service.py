from api.server import app
from fastapi.testclient import TestClient

def test_simple_check():
    client = TestClient(app)
    params = {'string':'diabetes'}
    response = client.post("/lookup",params=params)
    print(response.json())
    assert False
