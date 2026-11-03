# Documentation of CDB90

Documents about the CDB90 data, with OCR text. The OCR is made with LlamaParse by
`scripts/ocr.py`.

| Document | DTIC | Files |
|---|---|---|
| Database of Battles - Version 1990, the DTIC report documentation page (SF 298), April 30, 1991 | AD1038724 | `AD1038724.pdf`, `AD1038724.md` |
| CAA-SR-84-6, *Analysis of Factors That Have Influenced Outcomes of Battles and Wars: A Data Base of Battles and Engagements* (HERO, 1983-1984), six volumes | AD-B086 797 (Vol. I), AD-B087 718 to 722 (Vols. II to VI) | `hero/caa-sr-84-6-vol-N.md` and `.json` |

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
