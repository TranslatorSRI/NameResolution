# This Makefile contains all the instructions necessary to
# download Babel synonym files from a web location, create
# and load them into a Solr dataset and generate a Solr backup
# that can be used to start a NameRes instance.
#

# Configuration
SYNONYMS_URL=https://stars.renci.org/var/babel_outputs/2022dec2-2/synonyms/

# How much memory should Solr use.
SOLR_MEM=64G

# Where should the Solr PID file be created?
SOLR_PID=data/solr.pid

# SOLR_DIR should be set up to point to the Solr data directory (usually /var/solr)
# and SOLR_EXEC should be set up to point to the Solr executable.
# These will both be set up by the Dockerfile.

# All and clean targets.

.PHONY: all clean
all: 
	echo Done.

clean:
	rm -rf data/*

# This is a three step process.
#
# Step 1. Download an uncompress synonym files.
data/synonyms/done:
	wget -c -r -l1 -nd -P data/synonyms ${SYNONYMS_URL}
	gunzip data/synonyms/*.gz
	touch $@
	$(info Downloaded synonyms from ${SYNONYMS_URL})

# Step 2. Convert synonym files to JSON files.
CSV2JSON = python csv2json.py
SYNONYM_FILES = $(wildcard data/synonyms/*.txt)
JSON_FILES = $(addprefix data/json/,$(notdir $(SYNONYM_FILES:.txt=.json)))
data/json/%.json: data/synonyms/%.txt
	mkdir -p data/json
	$(CSV2JSON) $< $@ --sep "\t"
	$(info Converted $< to $@ using ${CSV2JSON}.)

data/json/done: data/synonyms/done ${JSON_FILES}
	touch data/json/done
	$(info Converted CSV files to ${JSON_FILES})

# Step 3. Start Solr server.
${SOLR_PID}:
	mkdir -p ${SOLR_DIR}/logs
	${SOLR_EXEC} -cloud -p 8983 -v -m ${SOLR_MEM} -s ${SOLR_DIR} >> ${SOLR_DIR}/logs/solr.txt 2>> ${SOLR_DIR}/logs/solr.err.txt
	while [ ! -s ${SOLR_PID} ]; do \
		${SOLR_EXEC} status | grep -Po 'Solr process \K([0-9]+)' > ${SOLR_PID}; \
	done
	$(info Solr started with PID file at ${SOLR_PID})
	cat ${SOLR_PID}

# Step 4. Load JSON files into Solr server.
data/setup-complete: data/json/done ${SOLR_PID}
	mkdir -p data/logs
	bash setup-and-load-solr.sh "data/json/*.json" >> data/logs/setup-and-load-solr.sh.log 2>> data/logs/setup-and-load-solr.sh.err.log && touch $@
	
data/start-solr-backup: data/setup-complete
	curl 'http://localhost:8983/solr/name_lookup/replication?command=backup&name=backup' && touch $@

# Step 5. Wait for the backup to complete.
data/check-solr-backup:
	curl 'http://localhost:8983/solr/name_lookup/replication?command=details'

.PHONY: stop-solr
stop-solr:
	rm ${SOLR_PID}
	${SOLR_EXEC} stop
	$(info Solr stopped.)
