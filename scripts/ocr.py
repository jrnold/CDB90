"""OCR PDFs with LlamaParse, writing Markdown and JSON next to each PDF (or into ``--out``).

Needs the ``LLAMA_CLOUD_API_KEY`` environment variable, and uploads each PDF to LlamaIndex's
service, so only run it on documents that can be shared (these are DTIC reports approved for
public release). With no arguments it OCRs the PDFs in ``src-data/docs/``; the ``ocr`` stage in
``dvc.yaml`` does that and is frozen, so ``dvc repro`` does not call the service. To rerun it:
``dvc unfreeze ocr && dvc repro ocr && dvc freeze ocr``.

For each PDF it writes ``<name>.md`` (one section per page) and ``<name>.json``
(``{"source", "tier", "pages": [{"page", "markdown"}]}``).

The six HERO volumes (CAA-SR-84-6) are too big for the repository, so their OCR text in
``src-data/docs/hero/`` was made by running this script on copies named ``caa-sr-84-6-vol-N.pdf``::

    uv run python -m scripts.ocr --out src-data/docs/hero caa-sr-84-6-vol-*.pdf
"""

import argparse
import json
from pathlib import Path

from llama_cloud import LlamaCloud

DOCS = Path("src-data/docs")
TIER = "cost_effective"


def parse_pages(client: LlamaCloud, pdf: Path) -> list[str]:
    """Return the Markdown of each page of ``pdf``."""
    with pdf.open("rb") as f:
        result = client.parsing.parse(
            tier=TIER, version="latest", upload_file=f, expand=["markdown"]
        )
    pages = result.markdown.pages if result.markdown else []
    texts: list[str] = []
    for number, page in enumerate(pages, 1):
        text = getattr(page, "markdown", None)  # a failed page has no markdown
        if text is None:
            message = f"{pdf.name}: page {number} failed to parse"
            raise RuntimeError(message)
        texts.append(text)
    return texts


def write_outputs(pdf: Path, pages: list[str], out: Path) -> None:
    """Write the Markdown and JSON versions of ``pages`` to ``out``."""
    out.mkdir(parents=True, exist_ok=True)
    header = (
        f"<!-- OCR of {pdf.name} by LlamaParse (tier {TIER}); see {pdf.name} for the original. -->"
    )
    sections = [f"<!-- page {number} -->\n\n{text}" for number, text in enumerate(pages, 1)]
    markdown = "\n\n".join([header, *sections]).rstrip() + "\n"
    (out / f"{pdf.stem}.md").write_text(markdown, encoding="utf-8")
    record = {
        "source": pdf.name,
        "tier": TIER,
        "pages": [{"page": number, "markdown": text} for number, text in enumerate(pages, 1)],
    }
    (out / f"{pdf.stem}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def main() -> None:
    """OCR the given PDFs, or every PDF in ``src-data/docs/``."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pdfs", nargs="*", type=Path, help="PDFs to OCR (default: src-data/docs)")
    parser.add_argument("--out", type=Path, help="output directory (default: next to each PDF)")
    args = parser.parse_args()
    client = LlamaCloud()
    for pdf in args.pdfs or sorted(DOCS.glob("*.pdf")):
        pages = parse_pages(client, pdf)
        write_outputs(pdf, pages, args.out or pdf.parent)
        print(f"{pdf.name}: {len(pages)} pages")


if __name__ == "__main__":
    main()
