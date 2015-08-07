# CDB90 Battle Dataset

A tidier and open-data version of CDB90 (CAA Database of Battles, Version 1990).
This used to be called CDB13, which I thought was an amusing name, but seemed to make people think I added to the CDB90 data.

The description of CDB90 from Helmbold (1993):

  A database of over 600 battles that were fought between 1600AD and
  1973AD. Descriptive data include battle name, date, and location;
  the strengths and losses on each side; identification of the victor;
  temporal duration of the battle; and selected environmental and
  tactical environment descriptors (such as type of fortifications,
  type of tactical scheme, weather conditions, width of front, etc.)

The directory `src-data/M000121` contains the original data from CDB90 as obtained from the NTIS.
The original datafiles are the `WKS` files.
However, since this is an archaic format, these were converted to `csv` files using LibreOffice (v. 4.4.3.2; BuildId: 88805f81e9fe61362df02b9941de8e38a9b5fd16; Locale: en_).

The directory `data` contains the revised data.
No major substantive changes were made to the data, nor were new battles added.
A brief summary of the revisions are:

- Minor changes to several values so that logical relationships hold. These are all the edits made in the revision CDB91 as described in Helmbold (1995) [DTIC reort ADA298124, p. 2-4](http://oai.dtic.mil/oai/oai?verb=getRecord&metadataPrefix=html&identifier=ADA298124). The remainder are a few other logical inconsistencies in the original data: e.g. total tanks must equal light battle tanks plus main battle tanks; tanks are 0, not missing prior to WWI.
- Reformatting the data from one of the messier spreadsheets that I have ever seen to tidy data. This means that there are seperate tables for battles, combatants, activity periods, etc.
- Additional variables linking the battles to other datasources such as the Correlates of War
- Different categorizations of wars, both from the original HERO dataset and my own categorization which is mostly consistent with the COW wars after 1815, and Wikipedia before 1815.

This dataset follows the [Data Package](http://www.dataprotocols.org/en/latest/data-packages.html) standard.

# Usage

To rebuild the data and documentation
```
$ python make_datapackage.py
$ ./create_data.sh
```

To create a ``sqlite3`` database with the data:
```
$ python load-sqlite . cdb13.sqlite3
```

# Licenses

- Code is [BSD-3](http://opensource.org/licenses/BSD-3-Clause) unless otherwise noted.
- Data is [odc-by](http://opendatacommons.org/licenses/by/).
- The original CDB90 data in `src-data/M000121` is Public Domain.

