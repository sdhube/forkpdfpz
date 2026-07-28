import re

import fitz


def make_token_pattern(token):
    # token like "/AA" must be followed by a PDF delimiter/whitespace,
    # not another regular character (which would mean it's a longer name)
    escaped = re.escape(token)
    return re.compile(escaped + r"(?=[\s/<>\[\]()]|$)")


TOKEN_PATTERNS = {t: make_token_pattern(t) for t in ("/JS", "/JavaScript", "/AA", "/OpenAction", "/XFA")}


def find_tokens(text):
    found = []
    for token, pattern in TOKEN_PATTERNS.items():
        if pattern.search(text):
            found.append(token)
    return found


def build_xref_page_map(doc):
    """Map each xref number to the page number(s) (1-indexed) it belongs to."""
    xref_to_pages = {}
    for pno in range(doc.page_count):
        pg = doc[pno]
        related = {pg.xref}
        for c in pg.get_contents():  # content stream xref(s)
            related.add(c)
        for annot in pg.annots():  # annotation object xrefs
            related.add(annot.xref)
        for xref in related:
            xref_to_pages.setdefault(xref, set()).add(pno + 1)
    return xref_to_pages


def scan_fitz_sanitized(pdf_path):
    doc = fitz.open(pdf_path)
    xref_to_pages = build_xref_page_map(doc)
    hits = []

    def location_for(xref):
        pages = xref_to_pages.get(xref)
        if pages:
            return f"page(s) {sorted(pages)}"
        if xref == doc.pdf_catalog():
            return "document catalog"
        return "unattached object (no page/catalog link found)"

    for xref in range(1, doc.xref_length()):
        # 1. Check the object's dictionary syntax
        try:
            obj = doc.xref_object(xref, compressed=False)
        except Exception as e:
            print(f"xref {xref}: could not read object ({e})")
            obj = ""
        for token in find_tokens(obj):
            hits.append((xref, token, "object", location_for(xref)))

        # 2. Check the object's decompressed stream content, if any
        try:
            stream = doc.xref_stream(xref)
        except Exception:
            stream = None
        if stream:
            try:
                text = stream.decode("latin-1", errors="replace")
            except Exception:
                text = ""
            for token in find_tokens(text):
                hits.append((xref, token, "stream", location_for(xref)))

    if not hits:
        print(f"{pdf_path}: no JS/action tokens found in any object or stream")
    else:
        print(f"{pdf_path}: found {len(hits)} hit(s)")
        for xref, token, where, loc in hits:
            print(f"--- xref {xref} [{where}] contains {token} — {loc} ---")
            if where == "object":
                print(doc.xref_object(xref, compressed=False))
            else:
                raw = doc.xref_stream(xref)
                print(raw[:500])  # truncate long streams
            print()

    doc.close()
    return hits
