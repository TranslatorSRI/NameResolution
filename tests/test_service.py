import logging

from api.server import app
from fastapi.testclient import TestClient

# Turn on debugging for tests.
logging.basicConfig(level=logging.DEBUG)

def test_simple_check():
    client = TestClient(app)
    params = {'string':'alzheimer', 'biolink_type': ''}
    response = client.post("/lookup",params=params)
    syns = response.json()
    #There are more than 10, but it should cut off at 10 if we don't give it a max?
    assert len(syns) == 10


def test_empty():
    """ Checks that calling NameRes without an input string return an empty list. """
    client = TestClient(app)
    response = client.get("/lookup", params={'string':''})
    syns = response.json()
    assert len(syns) == 0


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


def test_type_subsetting():
    client = TestClient(app)
    #Get everything with Parkinson (57)
    params = {'string': 'Parkinson', "limit": 100}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 57
    #Now limit to Disease (just 53)
    params = {'string': 'Parkinson', "limit": 100, "biolink_type": "biolink:Disease"}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 53
    #Now verify that NamedThing is everything
    params = {'string': 'Parkinson', "limit": 100, "biolink_type": "biolink:NamedThing"}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 57

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
    params = {'string': 'beta-secretase'}
    response = client.post("/lookup", params=params)
    syns = response.json()

    assert len(syns) == 1
    assert syns[0]["curie"] == 'CHEBI:74925'

    #no hyphen
    params = {'string': 'beta secretase'}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 2
    assert syns[0]["curie"] == 'CHEBI:74925'
    assert syns[1]["curie"] == 'MONDO:0011561'

def test_structure():
    client = TestClient(app)
    params = {'string': 'beta-secretase'}
    response = client.post("/lookup", params=params)
    syns = response.json()
    #do we get a preferred name and type?
    assert syns[0]["label"] == 'BACE1 inhibitor'
    assert syns[0]["types"] == ["biolink:NamedThing"]


def test_autocomplete():
    client = TestClient(app)
    params = {'string': 'beta-secretase', 'autocomplete': 'true'}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 1
    #do we get a preferred name and type?
    assert syns[0]["label"] == 'BACE1 inhibitor'
    assert syns[0]["types"] == ["biolink:NamedThing"]

    # Should also work with an incomplete search.
    params = {'string': 'beta-secretase', 'autocomplete': 'false'}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 2
    #do we get a preferred name and type?
    assert syns[0]['curie'] == 'CHEBI:74925'
    assert syns[0]["label"] == 'BACE1 inhibitor'
    assert syns[0]["types"] == ["biolink:NamedThing"]
    assert syns[1]['curie'] == 'MONDO:0011561'
    assert syns[1]["label"] == 'Alzheimer disease 6'
    assert syns[1]["types"][0] == "biolink:Disease"

    # Or even an incomplete query.
    params = {'string': 'beta-secreta', 'autocomplete': 'false'}
    response = client.post("/lookup", params=params)
    syns = response.json()
    assert len(syns) == 2
    #do we get a preferred name and type?
    assert syns[0]['curie'] == 'CHEBI:74925'
    assert syns[0]["label"] == 'BACE1 inhibitor'
    assert syns[0]["types"] == ["biolink:NamedThing"]
    assert syns[1]['curie'] == 'MONDO:0011561'
    assert syns[1]["label"] == 'Alzheimer disease 6'
    assert syns[1]["types"][0] == "biolink:Disease"

