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

from fastapi import FastAPI
import httpx
from starlette.middleware.cors import CORSMiddleware

LOGGER = logging.getLogger(__name__)
SOLR_HOST = os.getenv('SOLR_HOST', 'localhost')
SOLR_PORT = os.getenv('SOLR_PORT', '8983')

app = FastAPI(
    title='Name Resolver',
    description='Biomedical entity name resolution service',
    version='1.0.0',
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post('/lookup', response_model=Dict[str, List[str]], tags=['lookup'])
async def lookup_curies(string: str, offset: int = 0, limit: int = 10) -> Dict[str, List[str]]:
    """Look up curies from name or fragment."""
    fragments = string.split(' ')
    name_filters = ' AND '.join(f'name:/.*{re.escape(fragment)}.*/' for fragment in fragments)
    query = f'http://{SOLR_HOST}:{SOLR_PORT}/solr/name_lookup/select'
    params = {
        'q': name_filters,
        'start': 0,
        'rows': 0,
        'sort': 'length ASC',
        'json.facet': f'''{{
            categories : {{
                type: terms,
                field: curie,
                sort: "x asc",
                offset: {offset},
                limit: {limit},
                facet: {{
                    x: "min(length)"
                }},
                numBuckets: true
            }}
        }}'''
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.get(query, params=params)
    assert response.status_code < 300
    response = response.json()
    if not response['response']['numFound']:
        return dict()
    buckets = response['facets']['categories']['buckets']

    output = defaultdict(list)
    for bucket in buckets:
        curie = bucket['val']
        curie_filter = f'curie:/{re.escape(curie)}/'

        # get matching names - return these first
        filters = f'{curie_filter} AND ({name_filters})'
        query = f'http://{SOLR_HOST}:{SOLR_PORT}/solr/name_lookup/select'
        params = {
            'q': filters,
            'start': 0,
            'rows': 100,
            'sort': 'length ASC',
            'fl': 'name'
        }
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.get(query, params=params)
        docs = response.json()['response']['docs']
        names = [doc['name'] for doc in docs]
        output[curie].extend(names)

        # get non-matching names - return these second
        filters = f'{curie_filter} AND NOT ({name_filters})'
        query = f'http://{SOLR_HOST}:{SOLR_PORT}/solr/name_lookup/select'
        params = {
            'q': filters,
            'start': 0,
            'rows': 100,
            'sort': 'length ASC',
            'fl': 'name'
        }
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.get(query, params=params)
        docs = response.json()['response']['docs']
        names = [doc['name'] for doc in docs]
        output[curie].extend(names)
    return output
