"""Biomedical entity name resolution service.

1) split the input into fragments at spaces
  * The order does not matter
2) search for names including all fragments, case insensitive
3) sort by length, ascending
  * The curie with the shortest match is first, etc.
  * Matching names are returned first, followed by non-matching names
"""
import json
import logging
import os
import re
from typing import Dict, List

from fastapi import Body, FastAPI
from fastapi.responses import RedirectResponse
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

# If someone tries accessing /, we should redirect them to the Swagger interface.
@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url='/docs')


class Request(BaseModel):
    """Reverse-lookup request body."""

    curies: List[str]


@app.get(
    "/reverse_lookup",
    summary="Look up synonyms for a CURIE.",
    description="Returns a list of synonyms for a particular CURIE.",
    response_model=Dict[str, List[str]],
    tags=["lookup"],
)
async def lookup_names_get(
        request: Request = Body(..., example={
            "curies": ["MONDO:0005737", "MONDO:0009757"],
        }),
) -> Dict[str, List[str]]:
    """Look up curies from name or fragment."""
    return await reverse_lookup(request.curies)


@app.post(
    "/reverse_lookup",
    summary="Look up synonyms for a CURIE.",
    description="Returns a list of synonyms for a particular CURIE.",
    response_model=Dict[str, List[str]],
    tags=["lookup"],
)
async def lookup_names_post(
        request: Request = Body(..., example={
            "curies": ["MONDO:0005737", "MONDO:0009757"],
        }),
) -> Dict[str, List[str]]:
    """Look up curies from name or fragment."""
    return await reverse_lookup(request.curies)


async def reverse_lookup(curies) -> Dict[str, List[str]]:
    """Look up curies from name or fragment."""
    query = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/name_lookup/select"
    curie_filter = " OR ".join(
        f"curie:\"{curie}\""
        for curie in curies
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
        for curie in curies
    }
    for doc in response_json["response"]["docs"]:
        output[doc["curie"]].extend(doc["names"])
    return output

class LookupResult(BaseModel):
    curie:str
    label: str
    synonyms: List[str]
    types: List[str]


@app.get("/lookup",
     summary="Look up cliques for a fragment of a name or synonym.",
     description="Returns cliques with a name or synonym that contains a specified string.",
     response_model=List[LookupResult],
     tags=["lookup"]
)
async def lookup_curies_get(
        string: str,
        offset: int = 0,
        limit: conint(le=1000) = 10,
        biolink_type: str = None,
        only_prefixes: str = None
) -> List[LookupResult]:
    """Look up curies from name or fragment."""
    return await lookup(string, offset, limit, biolink_type, only_prefixes)


@app.post("/lookup",
    summary="Look up cliques for a fragment of a name or synonym.",
    description="Returns cliques with a name or synonym that contains a specified string.",
    response_model=List[LookupResult],
    tags=["lookup"]
)
async def lookup_curies_post(
        string: str,
        offset: int = 0,
        limit: conint(le=1000) = 10,
        biolink_type: str = None,
        only_prefixes: str = None
) -> List[LookupResult]:
    """Look up curies from name or fragment."""
    return await lookup(string, offset, limit, biolink_type, only_prefixes)

not_alpha = re.compile(r"[\W_]+")


async def lookup(string: str,
           offset: int = 0,
           limit: conint(le=1000) = 10,
           biolink_type: str = None,
           only_prefixes: str = ""
) -> List[LookupResult]:
    """Look up curies from name or fragment."""
    #This original code tokenizes on spaces, and then removes all other punctuation.
    # so x-linked becomes xlinked and beta-secretasse becomes betasecretase.
    # This turns out to be rarely what is wanted, especially because the tokenizer
    # isn't tokenizing this way.  I think that this may have come about due to chemical searching
    # but there is no documentation explaining the decision.  In the event that chemical or other punctuation
    # heavy searches start to fail, this may need to be revisited.
    #fragments = string.split(" ")
    #name_filters = " AND ".join(
    #    f"name:{not_alpha.sub('', fragment)}*"
    #    for fragment in fragments
    #)
    fragments = re.split(not_alpha,string)
    queries = [
        # Boost the preferred name by a factor of 10.
        # Using names:{fragment}* causes Solr to prioritize some odd results;
        # using names:{fragment} OR names:{fragment}* should cause it to still
        # include those results while prioritizing complete fragments.
        f"(preferred_name:{fragment}^10 OR names:{fragment})"
        for fragment in fragments if len(fragment) > 0
    ]
    query = " AND ".join(queries)

    # Apply filters as needed.
    filters = []
    if biolink_type:
        if biolink_type.startswith('biolink:'):
            biolink_type = biolink_type[8:]
        filters.append(f"types:{biolink_type}")

    if only_prefixes:
        prefix_filters = []
        for prefix in re.split('\\s*\\|\\s*', only_prefixes):
            # TODO: there are better ways to do a prefix search in Solr, such as using Regex,
            # but I can't hunt down the right syntax at the moment...
            prefix_filters.append(f"curie:/{prefix}:.*/")
        filters.append(" OR ".join(prefix_filters))

    # We should probably configure whether or not to apply the sort-by-shortest_name_length rule,
    # but since we don't have an alternative at the moment...

    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "filter": filters,
        "sort": "shortest_name_length ASC",
        "fields": "curie,names,preferred_name,types,shortest_name_length",
    }
    print(f"Query: {json.dumps(params)}")

    query_url = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/name_lookup/select"
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(query_url, json=params)
    if response.status_code >= 300:
        LOGGER.error("Solr REST error: %s", response.text)
        response.raise_for_status()
    response = response.json()
    output = [ {"curie": doc.get("curie", ""), "label":doc.get("preferred_name", ""), "synonyms": doc.get("names", []),
                "types": [f"biolink:{d}" for d in doc.get("types", [])]}
               for doc in response["response"]["docs"]]
    return output

# Override open api schema with custom schema
app.openapi_schema = construct_open_api_schema(app)
