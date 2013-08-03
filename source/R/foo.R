JSON_FIELDS <- function(x) {
  if (is(x, "Date")) {
    "date"
  } else if (is(x, "POSIXt")) {
    "datetime"
  } else if (is(x, "integer")) {
    "integer"
  } else if (is(x, "numeric")) {
    "number"
  } else if (is(x, "logical")) {
    "boolean"
  } else if (is(x, "factor")) {
    "string"
  } else if (is(x, "character")) {
    "string"
  } else {
    "binary"
  }
}

json_table_schema <- function(x) {
  llply(names(x),
        function(i) {
          ret <- list(id = i,
                      type = JSON_FIELDS(x[[i]]))
          if (!is.null(comment(x[[i]]))) {
            ret[["description"]] <- comment(x[[i]])
          }
          ret
        })
}
