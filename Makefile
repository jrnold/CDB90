R = Rscript
SRC_DIR = source/data
SRC_FILES = CDB90/CDB90.tsv local/war2.csv local/misc.csv local/cdb90_to_cow.csv local/duplicates.csv
SOURCES = $(addprefix $(SRC_DIR)/,$(SRC_FILES))
DATA_DIR = data

all: $(DATA_DIR)/battles.csv

$(DATA_DIR)/battles.csv: source/R/cdb13.R $(SOURCES)
	$(R) $^

clean:
	-rm -f data/*

.PHONY: clean all-data
