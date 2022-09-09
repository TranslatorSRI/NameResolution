# Loading NameResolution data

NameResolution data needs to be loaded as a compressed [Apache Solr](https://solr.apache.org/) database.
To create this dataset is a three-step process.

1. Set up a Solr server locally. The easiest way to do this is via Docker:

   ```shell
   $ docker run --name name_lookup -d -p 8983:8983 -t solr -DzkRun
   ```

2. Convert all the synonym text files into JSON document. To do this, you need to use the `csv2json.py` script
   included in this directory. By default, the Makefile expects the synonym files to be present in `data/synonyms`
   and writes out JSON files to `data/json`.

   ```shell
   $ pip install -r requirements.txt
   $ make
   ```
