library("readr")
library("jsonlite")
library("dplyr")

DIR <- "src-data/M000121/"
FILENAMES <- sort(dir("src-data/M000121/", pattern = "CDB90\\d{3}.*\\.csv$",
                      full.names = TRUE))

COLNAMES <- fromJSON("src-data/CDB90/cols.json")

data <- lapply(FILENAMES, function(f) {
  setNames(read.csv(f, skip = 8, header = FALSE,
                    colClasses = as.character(COLNAMES),
                    stringsAsFactors = FALSE),
           names(COLNAMES))
}) %>% bind_rows()
write.csv(data, file = "src-data/CDB90/CDB90-orig.csv", row.names = FALSE)

data2 <- read.delim("src-data/CDB90/CDB90.tsv",
                    colClasses = as.character(COLNAMES))
write.csv(data2, file = "src-data/CDB90/CDB90.csv", row.names = FALSE)

