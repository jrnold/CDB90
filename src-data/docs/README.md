# Documentation of CDB90

Documents about the CDB90 data, with OCR text. The OCR is made with LlamaParse by
`scripts/ocr.py`.

| Document | DTIC | Files |
|---|---|---|
| Database of Battles - Version 1990, the DTIC report documentation page (SF 298), April 30, 1991 | AD1038724 | `AD1038724.pdf`, `AD1038724.md` |
| CAA-SR-84-6, *Analysis of Factors That Have Influenced Outcomes of Battles and Wars: A Data Base of Battles and Engagements* (HERO, 1983-1984), six volumes | AD-B086 797 (Vol. I), AD-B087 718 to 722 (Vols. II to VI) | `hero/caa-sr-84-6-vol-N.md` and `.json` |
| Independent Review/Reassessment of Anomalous Data (IR/RAD), LFW Management Associates, 22 June 1987, four volumes | AD-A195 381 (Vol. 1), AD-A195 726 (Vol. 2), AD-A195 382 (Vol. 3), AD-A195 383 (Vol. 4) | `irrad/irrad-vol-N-ADAxxxxxx.pdf`, `.md` and `.json` |
| *New Engagement Data for the Breakpoints Data Base*, Richard C. Anderson, HERO / Data Memory Systems, 30 September 1988 (the source of battles 602 to 625) | AD-A201 404 | `hero-1988/new-engagement-data-ADA201404.pdf`, `.md` and `.json` |
| *Comparative Analysis of Armored Conflict Experience*, HERO, draft final report, 17 March 1967 | AD-873 137 to 139 (final report, not this draft) | `hero-1967/comparative-analysis-armored-conflict-1967.pdf`, `.md` and `.json` |
| *Comparative Analysis: Arab and Israeli Combat Performance, 1967 and 1973 Wars*, HERO, June 1976 | none found | `hero-1976/comparative-analysis-arab-israeli-combat-performance-1976.pdf`, `.md` and `.json` |
| *Forced Changes of Combat Posture*, Fain, Anderson, Dupuy, Hammerman and Hawkins, HERO / Data Memory Systems, 30 September 1988 (the study the new engagement data was made for) | AD-A201 405 | `hero-1988/forced-changes-of-combat-posture-ADA201405.pdf`, `.md` and `.json` |

All of them are marked "approved for public release", apart from the 1967 HERO draft, which is marked "Official Use Only" and is published by the Dupuy Institute (see [below](#the-1967-armored-conflict-study)). In the HERO volumes, DTIC's cover page
changed the distribution statement from B to A; the original limited-distribution markings
are still printed inside.

## The HERO volumes

The volumes describe each of the first 600 battles of CDB90 in a short narrative with the
date, the forces, the course of the action and the sources.

| Vol. | Contents | AD number | Pages |
|---|---|---|---|
| I | Main report | AD-B086 797 | 89 |
| II | Wars from 1600 through 1800 | AD-B087 718 | 260 |
| III | Wars from 1805 through 1900 | AD-B087 719 | 244 |
| IV | Wars from 1904 through 1940, including World War I | AD-B087 720 | 305 |
| V | World War II: North Africa, Italy, western Europe | AD-B087 721 | 188 |
| VI | World War II: France 1940, the Eastern Front and Japan; the 1967, 1968 and 1973 Arab-Israeli wars | AD-B087 722 | 245 |

The narratives are parsed into the table `battle_narratives` (see the data package): the `narrative`, `significance` and `sources` of each battle, with the source codes replaced by the full citations from the volumes' bibliography. The narratives of battles 602 to 625 are parsed from AD-A201 404 the same way (see below); it lists its sources by operation instead of by code. `scripts/narratives.py` does it, and `src-data/local/narrative_matches.csv` lists the few narratives matched to a battle by hand because of an OCR typo in the heading.

Battles 601 to 660 were added in CDB90 and are not described in these volumes; see
[Where battles 601 to 660 come from](#where-battles-601-to-660-come-from).

Each volume has two files: `.md` (Markdown, one section per page, marked with
`<!-- page N -->`) and `.json` (`{"source", "tier", "pages": [{"page", "markdown"}]}`). The PDFs
are 3 to 14 MB each, so they are not in the repository; to rerun the OCR, put copies named
`caa-sr-84-6-vol-N.pdf` in a directory and run

```
LLAMA_CLOUD_API_KEY=... uv run python -m scripts.ocr --out src-data/docs/hero caa-sr-84-6-vol-*.pdf
```

LlamaParse's `cost_effective` tier costs 3 credits per page (about 4,000 credits for the six
volumes). The text is much better than the PDFs' own text layer, but the scans are poor, so
check a number or a name against the PDF before relying on it.

## The IR/RAD volumes

The four volumes of the Independent Review/Reassessment of Anomalous Data (LFW Management Associates,
contract MDA903-86-C-0396) are in `irrad/`, as PDF (2.7 to 4.5 MB each), OCR Markdown and JSON, made like
the HERO volumes. The PDFs come from the Internet Archive's copy of the DTIC collection
(`archive.org/details/DTIC_ADA195381`, `_ADA195726`, `_ADA195382` and `_ADA195383`), and the volume
numbers are from their covers (they are not in AD-number order).

| Vol. | Contents | AD number | Pages |
|---|---|---|---|
| 1 | The Okinawa campaign, and appendices (the LFW team, glossary, XXIV Corps daily strengths and casualties, Japanese strengths, uncertainties in quantitative values) | AD-A195 381 | 105 |
| 2 | The Salerno and Volturno River campaigns | AD-A195 726 | 125 |
| 3 | The Anzio and Rome campaigns | AD-A195 382 | 88 |
| 4 | The Arab-Israeli wars, Northwest Europe, the Eastern Front | AD-A195 383 | 125 |

The IR/RAD is an independent reassessment of the data for 61 existing battles that were "statistically
anomalous" (a finding of the CHASE study), in 8 campaigns of World War II and the Arab-Israeli wars (the
campaigns of the four volumes). It adds no new battles: according to the CDB90 `README.TXT`, its data "differ
substantially" from those of the original data base, and the README does not say that CDB90 uses its numbers.
The volumes are campaign-level reassessments with many tables of daily strengths and casualties, not
battle-by-battle narratives like the HERO volumes.

## The 1967 armored conflict study

`hero-1967/` holds a 43-page draft of *Comparative Analysis of Armored Conflict Experience* (HERO, 17 March
1967), from the [Dupuy Institute](https://www.dupuyinstitute.org/pdf/020.pdf), which lists it as report 20. The
final report's AD numbers come from CAA-RP-93-2 (HERO-1967b), and no copy of it was found on the Internet Archive.
The draft has the summaries of the tank actions but not the appendix of engagements its contents page lists, and
printed page 5 of Section IV is missing. The text was transcribed from the page images by Claude Sonnet 5.5,
not by LlamaParse. It keeps the original spelling and errors. Check numbers against the PDF before relying on them.

## The 1976 Arab-Israeli report

`hero-1976/` holds *Comparative Analysis: Arab and Israeli Combat Performance, 1967 and 1973 Wars* (HERO, June
1976, 30 pages), from the [Dupuy Institute](https://www.dupuyinstitute.org/pdf/054.pdf), which lists it as report
54. It was prepared under contract DNA001-76-A-0089 and says it is not classified. The text was transcribed from
the page images by Claude Sonnet 5.5, not by LlamaParse. It keeps the original spelling and errors, and its errata
sheet is transcribed as a page but not applied to the tables. The dense tables and the handwritten Figure 17 are
the least reliable parts, so check a number against the PDF before relying on it.

## The annotated bibliography

`bibliography/` holds the OCR text (`.md`, one section per page, and `.json`) of CAA-RP-93-2,
*Personnel Attrition Rates in Historical Land Combat Operations: An Annotated Bibliography*
(Helmbold, June 1993, DTIC AD-A268 787, 476 pages). It lists and annotates the sources of the
historical combat data that CDB90 draws on. The PDF (20 MB) is not committed; it is in the DTIC
collection and in the author's Zotero library. The OCR is as LlamaParse returned it and has not
been corrected. The catalog of attrition data it accompanies (ADA279069) is software, not a PDF.

## Where battles 601 to 660 come from

The CDB90 `README.TXT` (`src-data/M000121/`, paragraph 2e) says that the Data Memory Systems report *New
Engagement Data for the Breakpoints Data Base* (30 September 1988), "in conjunction with independent research
by Mr. Robert McQuie of CAA, provided data on about 59 additional battles", which were added to CDB90. It is
not the IR/RAD (an earlier version of this README and of the data package said so, wrongly).

Searching the OCR text and the DTIC reports shows what documents them:

- 602 to 625 (Sidi Bou Zid, Kasserine Pass, Rapido, Bowling Alley, Mortain, Schmidt, Wahlerscheid,
  Krinkelt-Rocherath, Schnee Eifel, Our River): *New Engagement Data for the Breakpoints Data Base*
  (AD-A201 404) and *Forced Changes of Combat Posture* (AD-A201 405), both by the Historical Evaluation and Research
  Organization, 30 September 1988, now in `hero-1988/`. AD-A201 404 has an entry for each engagement with its
  date, a data sheet (war, location, start date and so on), who won and a "Significance" paragraph, laid out like
  the HERO volumes. Both are marked "Distribution Statement A, approved for public release".
- 601 (Mount Hermon III): a narrative in HERO Vol. VI.

The narratives of 602 to 625 are in `battle_narratives` (document `AD-A201404`). Its sources are the archival
records (record group 407 at the Washington National Records Center, "T" records microfilmed German records at
the National Archives, "R" records at the Bundesarchiv-Militararchiv in Freiburg), manuscripts and published
works that the report lists for each operation, so the engagements of an operation share one list.
AD-A201 404 also has a data sheet of 96 fields for each engagement; they are not in the data.
- 657 to 660 (France 1940): *Historical Characteristics of Combat for Wargames (Benchmarks)* (DTIC AD-A200 036)
  lists these battles and cites the 1967 armored conflict study as its source for France 1940, and the study's
  figures agree in part. Allied tanks and losses in 657, and the losses of 658, match. German tanks and losses
  in 657 do not (2,439 and 980 in CDB90, 2,683 and 1,080 in the study). 660 (Boos) matches "A Group Franc South
  of the Somme", with the two sides' tanks swapped in CDB90. The study has no section on 659 (Arras).
- 641 to 643 (Golan, 10 June 1967): their casualties and tank losses match figures 13 and 14 of *Comparative
  Analysis: Arab and Israeli Combat Performance, 1967 and 1973 Wars* (HERO, June 1976, now in `hero-1976/`). The same report lists most of 549 to
  601. Those battles have narratives in HERO Vol. VI, and the casualties of the ones compared (Rafah, Abu Ageila,
  El Arish, Bir Lahfan, Zaoura-Kala, Ahmadiyeh) differ from the report's, so they do not simply copy it, although
  Rafah's strengths and tank losses agree. Its scope is 1967 and 1973 only, so it is not the source of the 1948,
  1956, 1968 or 1982 battles.
- The rest of 626 to 660 (Korea, Targul Frumos, the 1948, 1956 and 1982 Israeli battles, Quang Tri): no
  documentation has been found. They are probably the result of McQuie's independent research, which the
  README does not cite a report for.
