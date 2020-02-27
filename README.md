# Biological entity lookup

## Docker setup

`docker-compose up`

## native setup

### Solr database

```bash
docker run --name name_lookup -d -p 8983:8983 -t solr -DzkRun
./setup.sh
```

### API

```bash
pip install -r requirements.txt
./main.sh
```

## examples

```bash
curl -X POST "http://localhost:6434/lookup?string=oxycod&offset=0&limit=10" -H "accept: application/json"
```
