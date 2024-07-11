"""Biomedical entity name resolution service.

1) split the input into fragments at spaces
  * The order does not matter
2) search for names including all fragments, case insensitive
3) sort by length, ascending
  * The curie with the shortest match is first, etc.
  * Matching names are returned first, followed by non-matching names
"""
import json
import logging, warnings
import os
import re
from typing import Dict, List, Union, Annotated

from fastapi import Body, FastAPI, Query
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

# ENDPOINT /
# If someone tries accessing /, we should redirect them to the Swagger interface.
@app.get("/", include_in_schema=False)
async def docs_redirect():
    """
    Redirect requests to `/` (where we don't have any content) to `/docs` (which is our Swagger interface).
    """
    return RedirectResponse(url='/docs')


@app.get("/status",
         summary="Get status and counts for this NameRes instance.",
         description="This endpoint will return status information and a list of counts from the underlying Solr "
                     "instance for this NameRes instance."
         )
async def status_get() -> Dict:
    """ Return status and count information from the underyling Solr instance. """
    return await status()


async def status() -> Dict:
    """ Return a dictionary containing status and count information for the underlying Solr instance. """
    query_url = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/admin/cores"
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.get(query_url, params={
            'action': 'STATUS'
        })
    if response.status_code >= 300:
        LOGGER.error("Solr error on accessing /solr/admin/cores?action=STATUS: %s", response.text)
        response.raise_for_status()
    result = response.json()

    # We should have a status for name_lookup_shard1_replica_n1.
    if 'status' in result and 'name_lookup_shard1_replica_n1' in result['status']:
        core = result['status']['name_lookup_shard1_replica_n1']

        index = {}
        if 'index' in core:
            index = core['index']

        return {
            'status': 'ok',
            'message': 'Reporting results from primary core.',
            'startTime': core['startTime'],
            'numDocs': index.get('numDocs', ''),
            'maxDoc': index.get('maxDoc', ''),
            'deletedDocs': index.get('deletedDocs', ''),
            'version': index.get('version', ''),
            'segmentCount': index.get('segmentCount', ''),
            'lastModified': index.get('lastModified', ''),
            'size': index.get('size', ''),
        }
    else:
        return {
            'status': 'error',
            'message': 'Expected core not found.'
        }


# ENDPOINT /reverse_lookup

class Request(BaseModel):
    """Reverse-lookup request body."""
    curies: List[str]


@app.get(
    "/reverse_lookup",
    summary="Look up synonyms for a CURIE.",
    description="Returns a list of synonyms for a particular CURIE.",
    response_model=Dict[str, Dict],
    tags=["lookup"],
)
async def lookup_names_get(
        curies: List[str]= Query(
            example=["MONDO:0005737", "MONDO:0009757"],
            description="A list of CURIEs to look up synonyms for."
        )
) -> Dict[str, Dict]:
    """Returns a list of synonyms for a particular CURIE."""
    return await reverse_lookup(curies)


@app.post(
    "/reverse_lookup",
    summary="Look up synonyms for a CURIE.",
    description="Returns a list of synonyms for a particular CURIE.",
    response_model=Dict[str, Dict],
    tags=["lookup"],
)
async def lookup_names_post(
        request: Request = Body(..., example={
            "curies": ["MONDO:0005737", "MONDO:0009757"],
        }),
) -> Dict[str, List[str]]:
    """Returns a list of synonyms for a particular CURIE."""
    return await reverse_lookup(request.curies)


async def reverse_lookup(curies) -> Dict[str, Dict]:
    """Returns a list of synonyms for a particular CURIE."""
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
        curie: {}
        for curie in curies
    }
    for doc in response_json["response"]["docs"]:
        output[doc["curie"]] = doc
    return output

class LookupResult(BaseModel):
    curie:str
    label: str
    synonyms: List[str]
    taxa: List[str]
    types: List[str]
    score: float
    clique_identifier_count: int


@app.get("/lookup",
     summary="Look up cliques for a fragment of a name or synonym.",
     description="Returns cliques with a name or synonym that contains a specified string.",
     response_model=List[LookupResult],
     tags=["lookup"]
)
async def lookup_curies_get(
        string: Annotated[str, Query(
            description="The string to search for."
        )],
        autocomplete: Annotated[bool, Query(
            description="Is the input string incomplete (autocomplete=true) or a complete phrase (autocomplete=false)?"
        )] = True,
        offset: Annotated[int, Query(
            description="The number of results to skip. Can be used to page through the results of a query.",
            # Offset should be greater than or equal to zero.
            ge=0
        )] = 0,
        limit: Annotated[int, Query(
            description="The number of results to skip. Can be used to page through the results of a query.",
            # Limit should be greater than or equal to zero and less than or equal to 1000.
            ge=0,
            le=1000
        )] = 10,
        biolink_type: Annotated[Union[str, None], Query(
            description="The Biolink type to filter to (with or without the `biolink:` prefix), e.g. `biolink:Disease` or `Disease`.",
            # We can't use `example` here because otherwise it gets filled in when filling this in.
            # example="biolink:Disease"
        )] = None,
        only_prefixes: Annotated[Union[str, None], Query(
            description="Pipe-separated, case-sensitive list of prefixes to filter to, e.g. `MONDO|EFO`.",
            # We can't use `example` here because otherwise it gets filled in when filling this in.
            # example="MONDO|EFO"
        )] = None,
        exclude_prefixes: Annotated[Union[str, None], Query(
            description="Pipe-separated, case-sensitive list of prefixes to exclude, e.g. `UMLS|EFO`.",
            # We can't use `example` here because otherwise it gets filled in when filling this in.
            # example="UMLS|EFO"
        )] = None,
        only_taxa: Annotated[Union[str, None], Query(
            description="Pipe-separated, case-sensitive list of taxa to filter, "
                        "e.g. `NCBITaxon:9606|NCBITaxon:10090|NCBITaxon:10116|NCBITaxon:7955`.",
            # We can't use `example` here because otherwise it gets filled in when filling this in.
            # example="NCBITaxon:9606|NCBITaxon:10090|NCBITaxon:10116|NCBITaxon:7955"
        )] = None
) -> List[LookupResult]:
    """
    Returns cliques with a name or synonym that contains a specified string.
    """
    return await lookup(string, autocomplete, offset, limit, biolink_type, only_prefixes, exclude_prefixes, only_taxa)


@app.post("/lookup",
    summary="Look up cliques for a fragment of a name or synonym.",
    description="Returns cliques with a name or synonym that contains a specified string.",
    response_model=List[LookupResult],
    tags=["lookup"]
)
async def lookup_curies_post(
        string: Annotated[str, Query(
            description="The string to search for."
        )],
        autocomplete: Annotated[bool, Query(
            description="Is the input string incomplete (autocomplete=true) or a complete phrase (autocomplete=false)?"
        )] = True,
        offset: Annotated[int, Query(
            description="The number of results to skip. Can be used to page through the results of a query.",
            # Offset should be greater than or equal to zero.
            ge=0
        )] = 0,
        limit: Annotated[int, Query(
            description="The number of results to skip. Can be used to page through the results of a query.",
            # Limit should be greater than or equal to zero and less than or equal to 1000.
            ge=0,
            le=1000
        )] = 10,
        biolink_type: Annotated[Union[str, None], Query(
            description="The Biolink type to filter to (with or without the `biolink:` prefix), e.g. `biolink:Disease` or `Disease`.",
            # We can't use `example` here because otherwise it gets filled in when filling this in.
            # example="biolink:Disease"
        )] = None,
        only_prefixes: Annotated[Union[str, None], Query(
            description="Pipe-separated, case-sensitive list of prefixes to filter to, e.g. `MONDO|EFO`.",
            # We can't use `example` here because otherwise it gets filled in when filling this in.
            # example="MONDO|EFO"
        )] = None,
        exclude_prefixes: Annotated[Union[str, None], Query(
            description="Pipe-separated, case-sensitive list of prefixes to exclude, e.g. `UMLS|EFO`.",
            # We can't use `example` here because otherwise it gets filled in when filling this in.
            # example="UMLS|EFO"
        )] = None,
        only_taxa: Annotated[Union[str, None], Query(
            description="Pipe-separated, case-sensitive list of taxa to filter, "
                        "e.g. `NCBITaxon:9606|NCBITaxon:10090|NCBITaxon:10116|NCBITaxon:7955`.",
            # We can't use `example` here because otherwise it gets filled in when filling this in.
            # example="NCBITaxon:9606|NCBITaxon:10090|NCBITaxon:10116|NCBITaxon:7955"
        )] = None
) -> List[LookupResult]:
    """
    Returns cliques with a name or synonym that contains a specified string.
    """
    return await lookup(string, autocomplete, offset, limit, biolink_type, only_prefixes, exclude_prefixes, only_taxa)


async def lookup(string: str,
           autocomplete: bool = False,
           offset: int = 0,
           limit: conint(le=1000) = 10,
           biolink_type: str = None,
           only_prefixes: str = "",
           exclude_prefixes: str = "",
           only_taxa: str = ""
) -> List[LookupResult]:
    """
    Returns cliques with a name or synonym that contains a specified string.

    :param autocomplete: Should we do the lookup in autocomplete mode (in which we expect the final word to be
        incomplete) or not (in which the entire phrase is expected to be complete, i.e. as an entity linker)?
    """
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

    # This version of the code replaces the previous facet-based multiple-query search NameRes used to have
    # (see https://github.com/TranslatorSRI/NameResolution/blob/v1.2.0/api/server.py#L79-L165)

    # For reasons we don't fully understand, we can put escaped special characters into the non-autocomplete
    # query but not the autocomplete query. So we handle those cases separately here. See
    # https://github.com/TranslatorSRI/NameResolution/issues/146 for a deeper dive into what's going on.
    string_lc = string.lower()

    string_lc_escape_groupings = string_lc.replace('(', '').replace(')', '').replace('"', '')
    string_lc_escape_everything = re.sub(r'([!(){}\[\]^"~*?:/+-])', r'\\\g<0>', string_lc) \
        .replace('&&', ' ').replace('||', ' ')

    # Construct query with an asterisk at the end so we look for incomplete terms.
    query = f'"{string_lc_escape_groupings}" OR ({string_lc_escape_everything}*)'

    # Apply filters as needed.
    # Biolink type filter
    filters = []
    if biolink_type:
        if biolink_type.startswith('biolink:'):
            biolink_type = biolink_type[8:]
        filters.append(f"types:{biolink_type}")

    # Prefix: only filter
    if only_prefixes:
        prefix_filters = []
        for prefix in re.split('\\s*\\|\\s*', only_prefixes):
            prefix_filters.append(f"curie:/{prefix}:.*/")
        filters.append(" OR ".join(prefix_filters))

    # Prefix: exclude filter
    if exclude_prefixes:
        prefix_exclude_filters = []
        for prefix in re.split('\\s*\\|\\s*', exclude_prefixes):
            prefix_exclude_filters.append(f"NOT curie:/{prefix}:.*/")
        filters.append(" AND ".join(prefix_exclude_filters))

    # Taxa filter.
    # only_taxa is like: 'NCBITaxon:9606|NCBITaxon:10090|NCBITaxon:10116|NCBITaxon:7955'
    if only_taxa:
        taxa_filters = []
        for taxon in re.split('\\s*\\|\\s*', only_taxa):
            taxa_filters.append(f'taxa:"{taxon}"')
        filters.append(" OR ".join(taxa_filters))

    params = {
        "query": {
            "edismax": {
                "query": query,
                # qf = query fields, i.e. how should we boost these fields if they contain the same fields as the input.
                # https://solr.apache.org/guide/solr/latest/query-guide/dismax-query-parser.html#qf-query-fields-parameter
                "qf": "preferred_name_exactish^100 names_exactish^50 preferred_name^10 names",
                # pf = phrase fields, i.e. how should we boost these fields if they contain the entire search phrase.
                # https://solr.apache.org/guide/solr/latest/query-guide/dismax-query-parser.html#pf-phrase-fields-parameter
                "pf": "preferred_name_exactish^150 names_exactish^70 preferred_name^20 names^10",
                # Boosts
                "bq": [],
                "boost": [
                    "log(clique_identifier_count)",
                    "div(1,shortest_name_length)"
                ],
            },
        },
        "sort": "score DESC, clique_identifier_count DESC, shortest_name_length ASC, curie_suffix ASC",
        "limit": limit,
        "offset": offset,
        "filter": filters,
        "fields": "*, score"
    }
    print(f"Query: {json.dumps(params, indent=2)}")

    query_url = f"http://{SOLR_HOST}:{SOLR_PORT}/solr/name_lookup/select"
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(query_url, json=params)
    if response.status_code >= 300:
        LOGGER.error("Solr REST error: %s", response.text)
        response.raise_for_status()
    response = response.json()
    output = [ LookupResult(curie=doc.get("curie", ""), label=doc.get("preferred_name", ""), synonyms=doc.get("names", []),
                score=doc.get("score", ""),
                taxa=doc.get("taxa", []),
                clique_identifier_count=doc.get("clique_identifier_count", 0),
                types=[f"biolink:{d}" for d in doc.get("types", [])])
               for doc in response["response"]["docs"]]
    # print(f"Response: {json.dumps(response, indent=2)}")

    return output

# Override open api schema with custom schema
app.openapi_schema = construct_open_api_schema(app)

# Set up opentelemetry if enabled.
if os.environ.get('OTEL_ENABLED', 'false') == 'true':
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    # from opentelemetry.sdk.trace.export import ConsoleSpanExporter

    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    # httpx connections need to be open a little longer by the otel decorators
    # but some libs display warnings of resource being unclosed.
    # these supresses such warnings.
    logging.captureWarnings(capture=True)
    warnings.filterwarnings("ignore", category=ResourceWarning)
    plater_service_name = os.environ.get('SERVER_NAME', 'infores:sri-name-resolver')
    assert plater_service_name and isinstance(plater_service_name, str)

    jaeger_exporter = JaegerExporter(
        agent_host_name=os.environ.get("JAEGER_HOST", "localhost"),
        agent_port=int(os.environ.get("JAEGER_PORT", "6831")),
    )
    resource = Resource(attributes={
        SERVICE_NAME: os.environ.get("JAEGER_SERVICE_NAME", plater_service_name),
    })
    provider = TracerProvider(resource=resource)
    # processor = BatchSpanProcessor(ConsoleSpanExporter())
    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider, excluded_urls=
                                       "docs,openapi.json")    
    HTTPXClientInstrumentor().instrument()
