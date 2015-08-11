library("jsonlite")
library("dplyr")

# Locations of the original csv files
DIR <- "../M000121/"
FILENAMES <- sort(dir(DIR, pattern = "CDB90\\d{3}.*\\.csv$",
                      full.names = TRUE))

# Names of columns
COLNAMES <- fromJSON("cols.json")

data <- lapply(FILENAMES, function(f) {
  setNames(read.csv(f, skip = 8, header = FALSE,
                    colClasses = as.character(COLNAMES),
                    stringsAsFactors = FALSE),
           names(COLNAMES))
}) %>% bind_rows()
write.csv(data, file = "CDB90-orig.csv", row.names = FALSE)

library("yaml")
patch <- yaml.load_file("patch.yaml")

# apply changes in patch.json
# for str, inst, rer, cas, finst, remove ","
# for isqno > 600, str[ad]mi, cas[ad]mi, str[ad]pl, cas[ad]pl set to missing
# Fix hours from 2400 to 0000
