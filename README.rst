CDB13 Battle Dataset
========================

Revised and cleaned version of the CDB90 database of battles.
The description from Helmbold (1993):

  A database of over 600 battles that were fought between 1600AD and
  1973AD. Descriptive data include battle name, date, and location;
  the strengths and losses on each side; identification of the victor;
  temporal duration of the battle; and selected environmental and
  tactical environment descriptors (such as type of fortifications,
  type of tactical scheme, weather conditions, width of front, etc.)

The directory `src-data/M000121` contains the original data from CDB90; the directory `data` contains the revised data.

This dataset follows the [Data Package](http://www.dataprotocols.org/en/latest/data-packages.html) standard.

Usage
================

To rebuild the data and documentation
```
$ python make_datapackage.py
$ ./create_data.sh
```

To create a ``sqlite3`` database with the data:
```
$ python load-sqlite . cdb13.sqlite3
```

Licenses
================

- Code is [BSD-3](http://opensource.org/licenses/BSD-3-Clause) unless otherwise noted.
- Data is [odc-by](http://opendatacommons.org/licenses/by/).
- The original CDB90 data in `src-data/M000121` is Public Domain.

