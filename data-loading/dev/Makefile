# This Makefile contains all the instructions necessary to
# download Babel synonym files from a web location, create
# and load them into a Solr dataset and generate a Solr backup
# that can be used to start a NameRes instance.
#

# Configuration
SYNONYMS_URL=https://stars.renci.org/var/babel_outputs/2022dec2/synonyms/

# How much memory should Solr use.
SOLR_MEM=12G

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

# Step 2. Convert synonym files to JSON files.
data/json/done:
	echo Convert synonym files to JSON files.

# Step 3. Start Solr server.
${SOLR_PID}:
	mkdir -p ${SOLR_DIR}/logs
	${SOLR_EXEC} -cloud -p 8983 -v -m ${SOLR_MEM} -s ${SOLR_DIR} >> ${SOLR_DIR}/logs/solr.txt 2>> ${SOLR_DIR}/logs/solr.err.txt
	while [ ! -s ${SOLR_PID} ]; do \
		${SOLR_EXEC} status | grep -Po 'Solr process \K([0-9]+)' > ${SOLR_PID}; \
	done
	cat ${SOLR_PID}

.PHONY: stop-solr
stop-solr:
	rm ${SOLR_PID}
	${SOLR_EXEC} stop

solr_backup:
	echo Running solr-backup.


