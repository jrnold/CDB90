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
