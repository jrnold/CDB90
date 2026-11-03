# Documentation of CDB90

Documents about the CDB90 data, with OCR text. The OCR is made with LlamaParse by
`scripts/ocr.py`.

| Document | DTIC | Files |
|---|---|---|
| Database of Battles - Version 1990, the DTIC report documentation page (SF 298), April 30, 1991 | AD1038724 | `AD1038724.pdf`, `AD1038724.md` |
| CAA-SR-84-6, *Analysis of Factors That Have Influenced Outcomes of Battles and Wars: A Data Base of Battles and Engagements* (HERO, 1983-1984), six volumes | AD-B086 797 (Vol. I), AD-B087 718 to 722 (Vols. II to VI) | `hero/caa-sr-84-6-vol-N.md` and `.json` |
| Independent Review/Reassessment of Anomalous Data (IR/RAD), LFW Management Associates, 22 June 1987, four volumes | AD-A195 381 (Vol. 1), AD-A195 726 (Vol. 2), AD-A195 382 (Vol. 3), AD-A195 383 (Vol. 4) | `irrad/irrad-vol-N-ADAxxxxxx.pdf`, `.md` and `.json` |

All of them are marked "approved for public release". In the HERO volumes, DTIC's cover page
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

The narratives are parsed into the table `battle_narratives` (see the data package): the `narrative`, `significance` and `sources` of each battle, with the source codes replaced by the full citations from the volumes' bibliography. `scripts/narratives.py` does it, and `src-data/local/narrative_matches.csv` lists the few narratives matched to a battle by hand because of an OCR typo in the heading.

Battles 601 to 660 come from the later IR/RAD review (DTIC AD-A195 381 to 383 and 726),
which is not here.

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

These are campaign-level reassessments with many tables of daily strengths and casualties, not battle-by-battle
narratives like the HERO volumes. They do **not** describe battles 601 to 660: the names of those battles
are not in them, apart from Mount Hermon (601).

## Where battles 601 to 660 are documented

Searching the OCR text and the DTIC reports found sources for part of them:

- 602 to 625 (Sidi Bou Zid, Kasserine Pass, Rapido, Bowling Alley, Mortain, Schmidt, Wahlerscheid,
  Krinkelt-Rocherath, Schnee Eifel, Our River): *New Engagement Data for the Breakpoints Data Base*
  (AD-A201 404) and *Forced Changes of Combat Posture* (AD-A201 405), both by the Historical Evaluation and Research
  Organization, 30 September 1988. They are not in this repository.
- 601 (Mount Hermon III): a narrative in HERO Vol. VI.
- 626 to 660 (Korea, Targul Frumos, the 1948, 1956, 1967 and 1982 Israeli battles, Quang Tri, France 1940): no
  documentation has been found.
