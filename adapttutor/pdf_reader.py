from __future__ import annotations

import fitz  # pymupdf

_MAX_WORDS = 4000


def extract_window(filepath: str, current_page: int, pages_before: int, pages_after: int) -> str:
    """
    Open a PDF at filepath, extract plain text from a window of pages centered on
    current_page (1-based, as in typical PDF UIs), and return a single string.

    Pages included: [current_page - pages_before, current_page + pages_after], clamped
    to the document. Text is concatenated in order, separated by blank lines between pages.

    Output is capped at 4000 words (whitespace-separated).
    """
    path = (filepath or "").strip()
    if not path:
        return ""

    before = max(0, int(pages_before))
    after = max(0, int(pages_after))
    center = int(current_page)
    if center < 1:
        center = 1

    try:
        doc = fitz.open(path)
    except Exception:
        return ""

    try:
        n = doc.page_count
        if n <= 0:
            return ""

        # 1-based center -> 0-based index, clamped into document
        idx = min(max(center - 1, 0), n - 1)
        start = max(0, idx - before)
        end = min(n - 1, idx + after)

        chunks: list[str] = []
        for i in range(start, end + 1):
            page = doc.load_page(i)
            text = page.get_text("text") or ""
            text = text.strip()
            if text:
                chunks.append(text)
    finally:
        doc.close()

    combined = "\n\n".join(chunks).strip()
    if not combined:
        return ""

    words = combined.split()
    if len(words) > _MAX_WORDS:
        words = words[:_MAX_WORDS]
    return " ".join(words)
