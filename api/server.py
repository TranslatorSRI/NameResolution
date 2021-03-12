"""Biomedical entity name resolution service.

1) split the input into fragments at spaces
  * The order does not matter
2) search for names including all fragments, case insensitive
3) sort by length, ascending
  * The curie with the shortest match is first, etc.
  * Matching names are returned first, followed by non-matching names
"""
from collections import defaultdict
import logging
import os
import re
from typing import Dict, List

from fastapi import Body, FastAPI
import httpx
from pydantic import BaseModel, conint
from starlette.middleware.cors import CORSMiddleware

from .apidocs import get_app_info, construct_open_api_schema

LOGGER = logging.getLogger(__name__)
SOLR_HOST = os.getenv("SOLR_HOST", "localhost")
SOLR_PORT = os.getenv("SOLR_PORT", "8983")

app = FastAPI(**get_app_info())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Request(BaseModel):
    """Reverse-lookup request body."""

    curies: List[str]


@app.post(
    "/reverse_lookup",
    response_model=Dict[str, List[str]],
    tags=["lookup"],
)
async def lookup_names(
        request: Request = Body(..., example={
            "curies": ["MONDO:0005737", "MONDO:0009757"],
        }),
) -> Dict[str, List[str]]:
    """Look up curies from name or fragment."""
    query = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/name_lookup/select"
    curie_filter = " OR ".join(
        f"curie:/{curie}/"
        for curie in request.curies
    )
    params = {
        "query": curie_filter,
        "limit": 1000000,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(query, json=params)
    response.raise_for_status()
    response_json = response.json()
    output = {
        curie: []
        for curie in request.curies
    }
    for doc in response_json["response"]["docs"]:
        output[doc["curie"]].append(doc["name"])
    return output


@app.post("/lookup", response_model=Dict[str, List[str]], tags=["lookup"])
async def lookup_curies(
        string: str,
        offset: int = 0,
        limit: conint(le=1000) = 10,
) -> Dict[str, List[str]]:
    """Look up curies from name or fragment."""
    fragments = string.split(" ")
    name_filters = " AND ".join(
        f"name:/.*{re.escape(fragment)}.*/"
        for fragment in fragments
    )
    query = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/name_lookup/select"
    params = {
        "query": name_filters,
        "limit": 0,
        "sort": "length ASC",
        "facet": {
            "categories": {
                "type": "terms",
                "field": "curie",
                "sort": "x asc",
                "offset": offset,
                "limit": limit,
                "facet": {
                    "x": "min(length)",
                },
                "numBuckets": True,
            }
        }
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(query, json=params)
    response.raise_for_status()
    response = response.json()
    if not response["response"]["numFound"]:
        return dict()
    buckets = response["facets"]["categories"]["buckets"]

    curie_filter = " OR ".join(
        f"curie:/{re.escape(bucket['val'])}/"
        for bucket in buckets
    )
    params = {
        "query": f"({curie_filter}) AND ({name_filters})",
        "limit": 1000000,
        "sort": "length ASC",
        "fields": "curie,name",
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(query, json=params)
    response.raise_for_status()
    output = defaultdict(list)
    for doc in response.json()["response"]["docs"]:
        output[doc["curie"]].append(doc["name"])
    params = {
        "query": f"({curie_filter}) AND NOT ({name_filters})",
        "limit": 1000000,
        "sort": "length ASC",
        "fields": "curie,name",
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(query, json=params)
    response.raise_for_status()
    for doc in response.json()["response"]["docs"]:
        output[doc["curie"]].append(doc["name"])
    return output

# Override open api schema with custom schema
app.openapi_schema = construct_open_api_schema(app)
