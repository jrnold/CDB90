#!/usr/bin/env bash
RSCRIPT=Rscript

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

$RSCRIPT create_data.R

