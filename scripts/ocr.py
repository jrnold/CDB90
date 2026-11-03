"""OCR the PDFs in ``src-data/docs/`` with LlamaParse, writing Markdown next to each PDF.

Needs the ``LLAMA_CLOUD_API_KEY`` environment variable, and uploads each PDF to LlamaIndex's
service, so only run it on documents that can be shared (these are DTIC reports approved for
public release). The ``ocr`` stage in ``dvc.yaml`` is frozen, so ``dvc repro`` does not call
the service; to rerun it: ``dvc unfreeze ocr && dvc repro ocr && dvc freeze ocr``.
"""

from pathlib import Path

from llama_cloud import LlamaCloud

DOCS = Path("src-data/docs")
TIER = "cost_effective"


def ocr(client: LlamaCloud, pdf: Path) -> str:
    """Return the Markdown of ``pdf``, one section per page."""
    with pdf.open("rb") as f:
        result = client.parsing.parse(
            tier=TIER, version="latest", upload_file=f, expand=["markdown"]
        )
    pages = result.markdown.pages if result.markdown else []
    sections = []
    for number, page in enumerate(pages, 1):
        text = getattr(page, "markdown", None)  # a failed page has no markdown
        if text is None:
            message = f"{pdf.name}: page {number} failed to parse"
            raise RuntimeError(message)
        sections.append(f"<!-- page {number} -->\n\n{text}")
    header = (
        f"<!-- OCR of {pdf.name} by LlamaParse (tier {TIER}); see {pdf.name} for the original. -->"
    )
    return "\n\n".join([header, *sections]).rstrip() + "\n"


def main() -> None:
    """OCR every PDF in ``src-data/docs/``."""
    client = LlamaCloud()
    for pdf in sorted(DOCS.glob("*.pdf")):
        pdf.with_suffix(".md").write_text(ocr(client, pdf), encoding="utf-8")


if __name__ == "__main__":
    main()
