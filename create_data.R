#!/usr/bin/env Rscript
# Create the database
suppressPackageStartupMessages({
    library("dplyr")
    library("stringr")
    library("lubridate")
    library("jsonlite")
})
DATA_DIR = "data"
SRC_DATA = "src-data"

## TODO: output battle, belligerent, atp
tomissing <- function(x, value=NA) {
  x[x %in% value] <- NA
  x
}

tomissing_neg <- function(x) {
  x[x < 0] <- NA
  x
}

expand.paste <- function(..., sep='') {
  apply(expand.grid(...), 1, paste, collapse = sep)
}

belligerent_col_names <- function(attacker) {
  if (attacker) postfix <- "a" else postfix <- "d"
  template <-
    c("nam%s", "co%s",
      "str%s", "code%s", "intst%s", "rerp%s",
      "cas%s", "finst%s", "cav%s", "tank%s",
      "lt%s", "mbt%s", "arty%s", "fly%s", "ctank%s",
      "carty%s", "cfly%s",
      paste0("pri%s", 1:3),
      paste0("sec%s", 1:3),
      paste0("reso%s", 1:3),
      paste0("str%s", c("pl", "mi")),
      paste0("cas%s", c("pl", "mi")),
      "ach%s")
  newnames <- sprintf(template, postfix)
  names(newnames) <- gsub("%s", "", template)
  newnames
}

battle_data <- function(cdb90, war2, cdb90_to_cow, misc, duplicates) {
  varnames <- c("isqno", "war",
                "name", "locn",
                "campgn",
                "postype",
                paste0("post", 1:2),
                "front",
                "depth",
                "time",
                "aeroa", "surpa",
                "cea", "leada", "trnga", "morala", "logsa", "momnta", "intela",
                "techa", "inita", "wina", "kmda",
                "crit", "quala", "resa", "mobila", "aira",
                "fprepa", "wxa", "terra", "leadaa", "plana", "surpaa",
                "mana", "logsaa", "fortsa", "deepa")
  x <- cdb90[ , varnames]
  x[["is_hero"]] <- x[["isqno"]] <= 600
  for (i in paste0("post", 1:2)) {
    x[[i]] <- tomissing(x[[i]], c("00", "OO"))
  }
  for (i in c("front", "depth", "time", "aeroa")) {
    x[[i]] <- tomissing(x[[i]], 9)
  }
  for (i in c('quala', 'resa', 'mobila', 'aira', 'fprepa', 'wxa', 'terra',
              'leadaa', 'plana', 'surpaa', 'mana', "aeroa", "surpa",
              'cea', 'leada', 'trnga', 'morala', 'logsa', 'momnta', 'intela', 'techa', 'inita', 'wina',
              'logsaa', 'fortsa', 'deepa', "kmda")) {
    x[[i]] <- tomissing_neg(x[[i]])
  }

  ## add new wars
  x <- mutate(merge(x, war2[ , c("isqno", "war2", "war3")], all.x=TRUE),
              war2 = ifelse(is.na(war2), war, war2),
              war3 = ifelse(is.na(war3), war, war3))

  # Add cdb90_wars
  x <- merge(x, cdb90_to_cow[ , c("isqno", "cow_warno", "cow_warname")],
             all.x = TRUE)

  # Add new wars
  misc <- misc[ , c("isqno", "war", "theater", "dbpedia")]
  names(misc) <- c("isqno", "cdb13_war", "cdb13_theater", "dbpedia")
  misc[["dbpedia"]] <-
    ifelse(misc[["dbpedia"]] != "",
           paste0("http://dbpedia.org/resource/",
                  as.character(misc[["dbpedia"]])),
           NA)
  x <- merge(x, misc, all.x = TRUE)

  # mark duplicates
  x <- merge(x, duplicates, all.x = TRUE)

  x
}

belligerent_data_0 <- function(cdb90, attacker, misc) {
  varnames <- belligerent_col_names(attacker)
  x <- cdb90[ , c("isqno", varnames)]
  names(x) <- c("isqno", names(varnames))
  x[["attacker"]] <- attacker
  # Missing commanders and names
  for (i in c("co", "nam")) {
    x[[i]] <- tomissing(x[[i]], "?")
  }
  x[["code"]] <- tomissing(x[["code"]], 0)
  for (i in c("str", "intst", "rerp", "cas", "finst",
              "cav", "tank", "lt", "mbt", "arty", "fly",
              "ctank", "carty", "cfly")) {
    x[[i]] <- tomissing(x[[i]], -1)
  }
  for (i in c(paste0("pri", 1:3),
              paste0("sec", 1:3),
              paste0("reso", 1:3))) {
    x[[i]] <- as.factor(tomissing(x[[i]], '00'))
  }

  if (attacker) {
    misc <- misc[ , c("isqno", "belligerenta")]
  } else {
    misc <- misc[ , c("isqno", "belligerentd")]
  }
  names(misc) <- c("isqno", "actors")
  x <- merge(x, misc, all.x=TRUE)
  
  x
}

belligerent_data <- function(cdb90, misc) {
  rbind(belligerent_data_0(cdb90, 1L, misc),
        belligerent_data_0(cdb90, 0L, misc))
}

daterange <- function(yyyy, mm, dd) {
  if (is.na(yyyy)) {
    list(min = NA, max = NA)
  } else {
    if (is.na(mm)) {
      list(min = as.Date(sprintf("%d-1-1", yyyy)),
           max = as.Date(sprintf("%d-1-1", yyyy + 1)))
    } else {
      date <- as.Date(sprintf("%d-%d-1", yyyy, mm))
      if(is.na(dd)) {
        list(min = date, max = date + months(1))
      } else {
        list(min = date, max = date)
      }
    }
  }
}

datetimerange <- function(yyyy, mm=NA, dd=NA, HH=NA, MM=NA) {
  if (is.na(yyyy)) {
    list(min = as.POSIXct(NA, origin = as.Date("1970-1-1"), tz = "UTC"),
         max = as.POSIXct(NA, origin = as.Date("1970-1-1"), tz = "UTC"))
  } else {
    if (is.na(mm)) {
      list(min = ymd_hm(sprintf("%d-1-1-00-00", yyyy), tz = "UTC", quiet=TRUE),
           max = ymd_hm(sprintf("%d-1-1-00-00", yyyy + 1, tz = "UTC", quiet=TRUE)))
    } else {
      if(is.na(dd)) {
        day <- ymd_hm(sprintf("%d-%d-1-00-00", yyyy, mm), tz = "UTC", quiet=TRUE)
        list(min = day, max = day + months(1))
      } else {
        if (is.na(HH)) {
          day <- ymd_hm(sprintf("%d-%d-%d-00-00", yyyy, mm, dd), tz = "UTC", quiet=TRUE)
          list(min = day, max = day + days(1))
        } else {
          if (is.na(MM)) {
            tm <- ymd_hm(sprintf("%d-%d-%d-%d-00", yyyy, mm, dd, HH), tz = "UTC", quiet=TRUE)
            list(min = tm, max = tm + hours(1))
          } else {
            tm <- ymd_hm(sprintf("%d-%d-%d-%d-%d",
                                 yyyy, mm, dd, HH, MM), tz = "UTC", quiet=TRUE)
              list(min = tm, max = tm)
          }
        }
      }
    }
  }
}

make_active_period <- function(x, i) {
  varlist <- c("atpbhr", "atpehr",
               "atpbyr", "atpeyr",
               "atpbmn", "atpemn",
               "atpbda", "atpeda")
  x <- x[ , paste0(varlist, i)]
  names(x) <- varlist

  if (is.na(x$atpbyr)) {
    NULL
  } else {
    duration_min <- duration_max <- NA
    duration_only <- 0
    if (is.na(x$atpbhr)) {
      HH1 <- MM1 <- HH2 <- MM2 <- NA
    } else if (x$atpbhr == 5000) {
      endhr <- (x$atpehr %/% 100) - 50
      endmn <- x$atpehr %% 100
      duration_min <- duration_max <- endhr * 60 + endmn
      duration_only <- 1
      HH1 <- MM1 <- HH2 <- MM2 <- NA
    } else {
      HH1 <- x$atpbhr %/% 100
      MM1 <- x$atpbhr %% 100
      HH2 <- x$atpehr %/% 100
      MM2 <- x$atpehr %% 100
    }
    start_time <- datetimerange(x$atpbyr, x$atpbmn, x$atpbda,
                                HH1, MM1)
    end_time <- datetimerange(x$atpeyr, x$atpemn, x$atpeda,
                              HH2, MM2)
    if (is.na(duration_min)) {
      duration_min <-
        pmax(0, as.numeric(difftime(end_time$min, start_time$max,
                                    units = "mins")))
      duration_max <- as.numeric(difftime(end_time$max, start_time$min,
                                          units = "mins"))
    }
    
    data.frame(atp_number = i,
               start_time_min = start_time$min, 
               start_time_max = start_time$max,
               end_time_min = end_time$min,
               end_time_max = end_time$max,
               duration_max = duration_max,
               duration_min = duration_min,
               duration_only = duration_only)
               
  }
}

make_all_active_periods <- function(x) {
  plyr::ldply(1:10, function(i) make_active_period(x, i = i))
}

atp_data <- function(cdb90) {
  for (i in expand.paste("atp", c("b", "e"), c("hr", "mn", "yr"),
                         as.character(1:10),
                         sep="")) {
    cdb90[[i]] <- tomissing(cdb90[[i]], c(99, 9999))
  }
  group_by(cdb90, isqno) %>% do(make_all_active_periods(.))
}

terra_data <- function(cdb90) {

  make_terra <- function(x, i) {
    terra <- toupper(gsub("O", "0", x[[paste0("terra", i)]]))
    if (terra == "000") {
      ret <- NULL
    } else {
      ret <- data.frame(terrano = i)
      for (j in 1:3) {
        ret[[sprintf("terra%d", j)]] <-
          tomissing(str_sub(terra, j, j), "0")
      }
    }
    ret
  }

  make_all_terra <- function(x) {
    plyr::ldply(1:2, function(i) make_terra(x, i = i))
  }

  group_by(cdb90, isqno) %>% do(make_all_terra(.))
  
}

wx_data <- function(cdb90) {

  make_wx <- function(x, i) {
    wx <- toupper(gsub("O", "0", x[[paste0("wx", i)]]))
    if (wx == "00000") {
      ret <- NULL
    } else {
      ret <- data.frame(wxno = i)
      for (j in 1:5) {
        ret[[sprintf("wx%d", j)]] <-
          tomissing(str_sub(wx, j, j), "0")
      }
    }
    ret
  }

  make_all_wx <- function(x) {
    plyr::ldply(1:3, function(i) make_wx(x, i = i))
  }

  group_by(cdb90, isqno) %>% do(make_all_wx(.))
  
}

writer <- function(x, file) {
  for (i in names(x)) {
    if (is(x[[i]], "factor")) {
      x[[i]] <- as.character(x[[i]])
    } else if (is(x[[i]], "Date")) {
      x[[i]] <- format(x[[i]], "%Y-%m-%d")
    } else if (is(x[[i]], "POSIXt")) {
      x[[i]] <- format(x[[i]], "%Y-%m-%dT%H:%M:%S")
    } else if (is(x[[i]], "logical")) {
      x[[i]] <- as.integer(x[[i]])
    }
  }
  write.csv(x, file = file, row.names = FALSE, na = "")
}

front_width_data <- function(cdb90) {

  make_front <- function(x, i) {
    vars <- sprintf(c("yr%d", "mo%d", "da%d", "hr%d",
                      "wofa%d", "wofd%d"), i)
    ret <- x[ , vars]
    names(ret) <- c("yr", "mo", "da", "hr", "wofa", "wofd")
    for (j in paste0("wof", c("a", "d"))) {
      ret[[j]] <- tomissing(ret[[j]], -1)
    }
    ret$front_number <- i
    times <- datetimerange(tomissing(ret$yr, 9999),
                           tomissing(ret$mo, 99),
                           tomissing(ret$da, 99),
                           tomissing(ret$hr %/% 100, 99),
                           tomissing(ret$hr %% 100, 99))
    ret$time_min <- times$min
    ret$time_max <- times$max
    select(ret, front_number, wofa, wofd, time_min, time_max)
  }

  make_all_fronts <- function(x) {
    plyr::ldply(1:3, function(i) make_front(x, i = i))
  }

  ret <-
      filter(plyr::ddply(cdb90, "isqno", make_all_fronts),
             ! is.na(wofa) | ! is.na(wofd))
  ret
}

#' x = active period data
make_battle_durations <- function(x) {
    (mutate(x, duration = 0.5 * (duration_min + duration_max))
     %>% group_by(isqno)
     %>% summarise(datetime_min = min(start_time_min)
                 , datetime_max = max(end_time_max)
                 , datetime = as.POSIXct(0.5 * (as.numeric(datetime_min) + as.numeric(datetime_max)), tz = "UTC", origin = as.Date("1970-1-1"))
                 , duration1 = as.numeric(difftime(max(start_time_max), min(start_time_min), units = "secs")) / 86400 + 1
                 , duration2 = min(sum(duration) / 1200, duration1)
                   )
     )
}

make_battle_actors <- function(x) {
    f <- function(x) {
        actors <- as.character(str_split(x$actors, pattern = fixed("|")))
        data_frame(isqno = x$isqno,
                   attacker = x$attacker,
                   n = seq_along(actors),
                   actor = actors)
    }
    rowwise(x) %>% do(f(.))
}

make_enum_tables <- function(filepath) {
    x <- fromJSON(filepath)
    ret <- list()
    for (i in names(x)) {
        xi <- x[[i]]
        ret[[i]] <-
            data_frame(value = names(xi),
                       description = as.character(xi))
    }
    ret
}

main <- function() {
  ## Raw datasets
  cdb90 <- read.delim(file.path(SRC_DATA, "/CDB90/CDB90.tsv"),
                      stringsAsFactors = FALSE)
  names(cdb90) <- tolower(names(cdb90))
  war2 <- read.csv(file.path(SRC_DATA, "/local/war2.csv"),
                   stringsAsFactors = FALSE)
  misc <- read.csv(file.path(SRC_DATA, "/local/misc.csv"),
                     stringsAsFactors = FALSE)
  cdb90_to_cow <- read.delim(file.path(SRC_DATA, "/local/cdb90_to_cow.csv"),
                             stringsAsFactors = FALSE)
  duplicates <-
    mutate(subset(mutate(read.csv(file.path(SRC_DATA, "/local/duplicates.csv"),
                                  stringsAsFactors = FALSE),
                         match = as.logical(match)),
                  match),
           isqno = isqno.x,
           parent = isqno.y)[ , c("isqno", "parent")]
  
  battles <- battle_data(cdb90, war2, cdb90_to_cow, misc, duplicates)
  belligerents <- belligerent_data(cdb90, misc)
  weather <- wx_data(cdb90)
  terrain <- terra_data(cdb90)
  active_periods <- atp_data(cdb90)
  front_widths <- front_width_data(cdb90)
  battle_durations <- make_battle_durations(active_periods)
  battle_actors <- make_battle_actors(belligerents)

  cat("Writing battles.csv\n")
  writer(battles, file.path(DATA_DIR, "battles.csv"))
  cat("Writing belligerents.csv\n")
  writer(belligerents, file.path(DATA_DIR, "belligerents.csv"))
  cat("Writing weather.csv\n")
  writer(weather, file.path(DATA_DIR, "weather.csv"))
  cat("Writing terrain.csv\n")
  writer(terrain, file.path(DATA_DIR, "terrain.csv"))
  cat("Writing active_periods.csv\n")
  writer(active_periods, file.path(DATA_DIR, "active_periods.csv"))
  cat("Writing front_widths.csv\n")
  writer(front_widths, file.path(DATA_DIR, "front_widths.csv"))
  cat("Writing battle_durations.csv\n")
  writer(battle_durations, file.path(DATA_DIR, "battle_durations.csv"))  
  cat("Writing battle_actors.csv\n")
  writer(battle_actors, file.path(DATA_DIR, "battle_actors.csv"))

  # Writing out variable levels
  enums <- make_enum_tables(file.path(SRC_DATA, "variable_levels.json"))
  for (i in names(enums)) {
      outfile <- file.path(DATA_DIR, sprintf("enum_%s.csv", i))
      cat(sprintf("writing %s\n", outfile))
      writer(enums[[i]], outfile)
  }
  
}

main()

