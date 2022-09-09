# A Makefile for building JSON files for the tab-delimited Babel synonym files.

SYNONYMS_DIR=data/synonyms
JSON_DIR=data/json
SYNONYMS_FILES=$(wildcard $(SYNONYMS_DIR)/*.txt)
JSON_FILES=$(addprefix $(JSON_DIR)/,$(notdir $(SYNONYMS_FILES:.txt=.json)))

CSV2JSON=python csv2json.py

.PHONY:all clean
all: $(JSON_FILES)
clean:
	rm -rf $(JSON_FILES)

$(JSON_FILES): $(SYNONYMS_FILES)
	echo $(CSV2JSON) $^ $@ --sep "\t"
