The file `CDB90.csv` is the CDB90 data after the multiple files have been concatenated into a single file, and some manual edits have been made.
These edits include a few changes to casualties and strengths (as in CDB91), and some other minor edits.
This was done this way, because, ..., well, it was easier.
I may go back and generate it all by script.
In the meantime, the following generates a csv diff between `CDB90.csv` and the original CDB90 data.
```console
$ Rscript concat_cdb90.R
$ daff --output patch.csv CDB90-orig.csv CDB90.csv
$ daff render --output patch.html patch.csv
```
This requires installing [daff](https://github.com/paulfitz/daff), R, and R packages jsonlite and dplyr.
To view the edits made open `patch.html` in a browser.

