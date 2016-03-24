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
  
The original documentation for the CDB90 dataset is in [src-data/M000121/README.TXT](https://github.com/jrnold/CDB90/tree/master/src-data/M000121).


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

To build the data csv's, documentation, and create a SQLite database with the data, run:
```
$ ./build.sh
```

# References

- CAA Study Report CAA-SR-84-6, "Analysis of Factors That Have Influenced Outcomes of Battles and Wars: A Data Base of Battles and Engagements," September 1984: AD-B086-797L, AD-B087-718L, AD-B087-719L, AD-B087-720L, AD-B087-721L, AD-B087-722L
- HERO Report Number 129, "Combat History Analysis Study Effort (CHASE) Data Enhancement Study (CDES)," 31 January 1986, AD-A175-712, AD-A175-713, AD-A175-714, AD-A175-715, AD-A175-716
- Data Base Error Correction (DBEC)," 23 January 1987. It was prepared for CAA under Purchase Order Number MDA903-86-M-8560 and is available from DTIC under accession number AD-A176-750.
- FW Management Associates, Inc. Report "Independent Review/Reassessment of Anomalous Data (IR/RAD)," 22 June 1987, in four volumes. It was prepared for CAA under Contract Number MDA903-86-C-0396. It is available from DTIC under the following accession numbers: AD-???-??? (Volume I), AD-195-726 (Volume II), AD-???-??? (Volume III), and AD-???-??? (Volume IV)
- Data Memory Systems Incorporated report, "New Engagement Data for the Breakpoints Data Base," prepared for the US Army Concepts Analysis Agency under Contract No. MDA903-87-C-0807, 30 September 1988.
- Robert Helmbold. 1993. "Personnel Attrition Rates in Historical Land Combat Operations: A Catalog of Attrition and Casualty Data Bases on Diskettes Usable with Personal Computers." [DTIC ADA279069](http://www.dtic.mil/docs/citations/ADA279069).
- Robert Helmbold. 1995. "Personnel Attrition Rates in Historical Land Combat Operations. Some Empirical Relations among Force Sizes, Battle Durations" [DTIC AD-A268 787](http://handle.dtic.mil/100.2/ADA298124).

# Licenses

- Code is [BSD-3](http://opensource.org/licenses/BSD-3-Clause) unless otherwise noted.
- Data is [odc-by](http://opendatacommons.org/licenses/by/).
- The original CDB90 data in `src-data/M000121` is Public Domain.

