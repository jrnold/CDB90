#!/usr/bin/env bash
RSCRIPT=Rscript
PYTHON=python
SQLITE_DB=cdb90.sqlite3

DATA_DIR=data
SRC_DIR=src-data

if [ -d "$DATA_DIR" ]
then
    read -p "Delete contents of directory \"$DATA_DIR\" (y/n)?" yn
    case "$yn" in
	[Yy]* ) rm -rf $DATA_DIR/* ;;
	[Nn]* ) echo "exiting"; exit 1 ;;
	* ) echo "answer yes or no" ;;
    esac
else
    echo "Creating directory \"$DATA_DIR\""
    mkdir -p "$DATA_DIR"
fi


# create files in ./data
$RSCRIPT create_data.R

# rebuild datapackage.json
echo "rebuilding datapackage.json"
$PYTHON make_datapackage.py

# Load csv files into sqlite database
if [ -e "$SQLITE_DB" ]
then
    rm $SQLITE_DB
fi
echo "loading data/*csv into SQLite database $SQLITE_DB"
$PYTHON load-sqlite.py datapackage.json $SQLITE_DB

