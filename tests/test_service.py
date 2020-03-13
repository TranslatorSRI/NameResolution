from api.server import app
from fastapi.testclient import TestClient

def test_simple_check():
    client = TestClient(app)
    params = {'string':'alzheimer'}
    response = client.post("/lookup",params=params)
    syns = response.json()
    #There are more than 10, but it should cut off at 10 if we don't give it a max?
    assert len(syns) == 10

def xtest_max():
    client = TestClient(app)
    params = {'string': 'alzheimer'}
    response = client.post("/lookup", params=params)
    syns = response.json()
    # There are more than 10, but it should cut off at 10 if we don't give it a max?
    assert len(syns) == 10
