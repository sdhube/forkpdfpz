"""
pdf_select_info_source.py

Merges multiple "info source" results into a single PdfManifestEntry.

Workflow:
    1. Start from an empty manifest_object (new_empty_manifest_entry()).
    2. For each info source available (filename parsing, PDF metadata,
       ISBN lookup, OCR, etc.), build a PdfManifestEntry with whatever
       fields that source was able to determine, and call
       append_info_source(manifest_object, info_source).
    3. Empty fields on manifest_object are simply filled in from the
       info source. Non-empty fields are reconciled via
       update_old_by_new(), which currently just keeps the existing
       value if it agrees with the new one (a true conflict-resolution
       policy can be layered in later).
"""

from dataclasses import dataclass, fields, replace
from typing import Any


@dataclass
class PdfManifestEntry:
    valid_pdf: bool
    file: str
    title: str
    author: str
    size: int
    optimized: bool
    isbn: str
    year: str

    # Extra field beyond the Rust struct: ISBN with hyphens/spaces stripped and
    # the check digit uppercased, for lookup/dedup use. `isbn` stays exactly
    # as it appears in the PDF text.
    isbn_normalized: str = ""

    # Extra field beyond the Rust struct: "<title>-<author>-<year>"
    book_id: str = ""

    # Extra field beyond the Rust struct: source format, currently always "pdf"
    book_type: str = "pdf"


def new_empty_manifest_entry() -> PdfManifestEntry:
    """Return a PdfManifestEntry with every field at its 'empty' value."""
    return PdfManifestEntry(
        valid_pdf=False,
        file="",
        title="",
        author="",
        size=0,
        optimized=False,
        isbn="",
        year="",
        isbn_normalized="",
        book_id="",
        book_type="pdf",
    )


def _is_empty(value: Any) -> bool:
    """
    Field-agnostic emptiness check used to decide whether a field on
    manifest_object is still unset and can simply be overwritten.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, bool):
        # Booleans have no "empty" state -- False is a meaningful value,
        # not an unset one.
        return False
    if isinstance(value, int):
        return value == 0
    return False


def update_file_with_policy(old: str, new: str) -> str:
    """Resolve `file` when both sides already have a value."""
    if old == new:
        return old
    return old


def update_title_with_policy(old: str, new: str) -> str:
    """Resolve `title` when both sides already have a value."""
    if old == new:
        return old
    return old


def update_author_with_policy(old: str, new: str) -> str:
    """Resolve `author` when both sides already have a value."""
    if old == new:
        return old
    return old


def update_isbn_with_policy(old: str, new: str) -> str:
    """Resolve `isbn` when both sides already have a value."""
    if old == new:
        return old
    return old


def update_year_with_policy(old: str, new: str) -> str:
    """Resolve `year` when both sides already have a value."""
    if old == new:
        return old
    return old


# Fields that always take info_source's value directly, with no
# empty-check and no policy function -- a plain overwrite.
_DIRECT_UPDATE_FIELDS = {
    "valid_pdf",
    "size",
    "optimized",
    "isbn_normalized",
    "book_id",
    "book_type",
}

# Dispatch table: field name -> the per-field policy function to call
# when manifest_object already has a non-empty value for that field.
# Only fields NOT in _DIRECT_UPDATE_FIELDS go through this.
_FIELD_UPDATERS = {
    "file": update_file_with_policy,
    "title": update_title_with_policy,
    "author": update_author_with_policy,
    "isbn": update_isbn_with_policy,
    "year": update_year_with_policy,
}


def append_info_source(
    manifest_object: PdfManifestEntry,
    info_source: PdfManifestEntry,
) -> PdfManifestEntry:
    """
    Merge `info_source` into `manifest_object` and return the result.

    Rules per field:
      - field is in _DIRECT_UPDATE_FIELDS  -> always overwrite with
        info_source's value, no empty-check, no policy function.
      - manifest_object's field is empty   -> take info_source's value.
      - manifest_object's field is set     -> resolve via the matching
        update_<field>_with_policy function (e.g. update_title_with_policy).

    Neither input is mutated; a new PdfManifestEntry is returned.
    """
    updates = {}
    for f in fields(manifest_object):
        name = f.name
        new_value = getattr(info_source, name)

        if name in _DIRECT_UPDATE_FIELDS:
            updates[name] = new_value
            continue

        old_value = getattr(manifest_object, name)
        if _is_empty(old_value):
            updates[name] = new_value
        else:
            updates[name] = _FIELD_UPDATERS[name](old_value, new_value)

    return replace(manifest_object, **updates)


if __name__ == "__main__":
    # Small smoke test / usage example.
    manifest = new_empty_manifest_entry()

    from_filename = PdfManifestEntry(
        valid_pdf=True,
        file="clean-code.pdf",
        title="Clean Code",
        author="",
        size=0,
        optimized=False,
        isbn="",
        year="2008",
    )

    from_metadata = PdfManifestEntry(
        valid_pdf=True,
        file="",
        title="Clean Code",
        author="Robert C. Martin",
        size=4_200_000,
        optimized=True,
        isbn="978-0-13-235088-4",
        year="2008",
    )

    manifest = append_info_source(manifest, from_filename)
    manifest = append_info_source(manifest, from_metadata)

    print(manifest)
