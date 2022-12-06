# This Makefile contains all the instructions necessary to
# download Babel synonym files from a web location, create
# and load them into a Solr dataset and generate a Solr backup
# that can be used to start a NameRes instance.
#

# Configuration
SYNONYMS_URL=https://stars.renci.org/var/babel_outputs/2022dec2/synonyms/

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

solr_backup:
	echo Running solr-backup.


