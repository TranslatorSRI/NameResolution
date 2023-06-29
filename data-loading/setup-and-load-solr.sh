#!/usr/bin/env bash

SOLR_PORT=8983

is_solr_up(){
    echo "Checking if solr is up on http://localhost:$SOLR_PORT/solr/admin/cores"
    http_code=`echo $(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$SOLR_PORT/solr/admin/cores")`
    echo $http_code
    return `test $http_code = "200"`
}

wait_for_solr(){
    while ! is_solr_up; do
        sleep 3
    done
}

wait_for_solr

# add collection
curl -X POST 'http://localhost:8983/solr/admin/collections?action=CREATE&name=name_lookup&numShards=1&replicationFactor=1'

# do not autocreate fields
curl 'http://localhost:8983/solr/name_lookup/config' -d '{"set-user-property": {"update.autoCreateFields": "false"}}'

# add lowercase text type
curl -X POST -H 'Content-type:application/json' --data-binary '{
    "add-field-type" : {
        "name": "LowerTextField",
        "class": "solr.TextField",
        "positionIncrementGap": "100",
        "analyzer": {
            "tokenizer": {
                "class": "solr.StandardTokenizerFactory"
            },
            "filters": [{
                "class": "solr.LowerCaseFilterFactory"
            }]
        }
    }
}' 'http://localhost:8983/solr/name_lookup/schema'

# add fields
curl -X POST -H 'Content-type:application/json' --data-binary '{
    "add-field": [
        {
            "name":"names",
            "type":"LowerTextField",
            "stored":true,
            "multiValued":true
        },
        {
            "name":"curie",
            "type":"string",
            "stored":true
        },
        {
            "name":"preferred_name",
            "type":"string",
            "stored":true
        },
        {
            "name":"types",
            "type":"string",
            "stored":true
            "multiValued":true
        },
        {
            "name":"shortest_name_length",
            "type":"integer",
            "stored":true
        }
    ] }' 'http://localhost:8983/solr/name_lookup/schema'

# add data
for f in $1; do
echo "Loading $f..."
curl -X POST -H 'Content-Type: application/json' -d @$f \
    'http://localhost:8983/solr/name_lookup/update/json/docs?processor=uuid&uuid.fieldName=id&commit=true'
done
echo "Check solr"
curl -s --negotiate -u: 'localhost:8983/solr/name_lookup/query?q=*:*&rows=0'

