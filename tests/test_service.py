from api.server import app
from fastapi.testclient import TestClient

def test_simple_check():
    client = TestClient(app)
    params = {'string':'alzheimer'}
    response = client.post("/lookup",params=params)
    syns = response.json()
    #There are more than 10, but it should cut off at 10 if we don't give it a max?
    assert len(syns) == 10

def test_limit():
    client = TestClient(app)
    params = {'string': 'alzheimer', 'limit': 1}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 1
    params2 = {'string': 'alzheimer', 'limit': 100}
    response = client.post("/lookup", params=params2)
    syns = response.json()
    #There are actually 31 in the test file
    assert len(syns) == 31

def test_offset():
    client = TestClient(app)
    #There are 31 total.  If we say, start at 20 and give me then next 100 , we should get 11
    params = {'string': 'alzheimer', 'limit': 100, 'offset': 20}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 11

def test_hyphens():
    """The test data contains CHEBI:74925 with name 'beta-secretase inhibitor.
    Show that we can find it with or without the hyphen"""
    client = TestClient(app)
    #with hyphen
    params = {'string': 'beta secretase'}
    response = client.post("/lookup", params=params)
    syns = response.json()
    print(syns)
    assert len(syns) == 1
    assert list(syns.keys())[0] == 'CHEBI:74925'
    #no hyphen
    params = {'string': 'beta secretase'}
    response = client.post("/lookup", params=params)
    syns = response.json()
    print(syns)
    assert len(syns) == 1
    assert list(syns.keys())[0] == 'CHEBI:74925'

