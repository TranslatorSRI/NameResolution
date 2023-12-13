# Name resolution service

This service takes lexical strings and attempts to map them to identifiers (curies) from a vocabulary or ontology.  
The lookup is not exact, but includes partial matches.

Multiple results may be returned representing possible conceptual matches, but all of the identifiers have been 
correctly normalized using the [NodeNormalization service](https://nodenormalization-sri.renci.org/apidocs).

See the documentation [notebook](documentation/NameResolution.ipynb) for examples of use.

## Docker setup

`docker-compose up`

## native setup

### Solr database

See instructions in the `data-loading/` directory.

### API

```bash
pip install -r requirements.txt
./main.sh
```

### Kubernetes

Helm charts can be found at https://github.com/helxplatform/translator-devops/helm/r3

## examples

```bash
curl -X POST "http://localhost:6434/lookup?string=oxycod&offset=0&limit=10" -H "accept: application/json"
```

## Configuration

NameRes can be configured by setting environmental variables:

* `SOLR_HOST` and `SOLR_PORT`: Hostname and port for the Solr database containing NameRes information.
* `SERVER_NAME`: The name of this server (defaults to `infores:sri-name-resolver`)
* `SERVER_ROOT`: The server root (defaults to `/`)
* `MATURITY_VALUE`: How mature is this NameRes (defaults to `maturity`, e.g. `development`)
* `LOCATION_VALUE`: Where is this NameRes setup (defaults to `location`, e.g. `RENCI`)
* `OTEL_ENABLED`: Turn on Open TELemetry (default: False)
    * `JAEGER_HOST` and `JAEGER_PORT`: Hostname and port for the Jaegar instance to provide telemetry to.
    * `JAEGER_SERVICE_NAME`: The name of this service (defaults to the value of `SERVER_NAME`)
