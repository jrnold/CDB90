#!/usr/bin/env bash
PYTHON=python
SQLITE_DB=cdb90.sqlite3
DAFF=daff.py

DATA_DIR=data
SRC_DIR=src-data

if [[ -d "${DATA_DIR}" ]]; then
  read -r -p "Delete contents of directory \"${DATA_DIR}\" (y/n)?" yn
  case "${yn}" in
    [Yy]*) find "${DATA_DIR}" -mindepth 1 ! -name LICENSE.md -delete ;;
    [Nn]*)
      echo "exiting"
      exit 1
      ;;
    *) echo "answer yes or no" ;;
  esac
else
  echo "Creating directory \"${DATA_DIR}\""
  mkdir -p "${DATA_DIR}"
fi

# create files in ./data
"${PYTHON}" create_data.py

# download battle coordinates (needs network access)
"${PYTHON}" scripts/coordinates.py

# rebuild datapackage.json
echo "rebuilding datapackage.json"
"${PYTHON}" make_datapackage.py

# Making daff diffs
echo "diffing original and patched CDB90 csvs"
"${DAFF}" diff --output "${SRC_DIR}/CDB90/diff.csv" --context 0 "${SRC_DIR}/CDB90/cdb90-orig.csv" "${SRC_DIR}/CDB90/cdb90-patched.csv"
"${DAFF}" render --output "${SRC_DIR}/CDB90/diff.html" "${SRC_DIR}/CDB90/diff.csv"

# Load csv files into sqlite database
if [[ -e "${SQLITE_DB}" ]]; then
  rm "${SQLITE_DB}"
fi
echo "loading data/*csv into SQLite database ${SQLITE_DB}"
"${PYTHON}" load-sqlite.py datapackage.json "${SQLITE_DB}"
