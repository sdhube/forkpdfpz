from pdfpz.core.class_book_manifest import PdfManifestEntry
from pdfpz.core.merge import merge


def _entry(name, **overrides):
    e = PdfManifestEntry.new_empty_manifest_entry()
    e.name = name
    for k, v in overrides.items():
        setattr(e, k, v)
    return e


def test_merge_skips_existing_names():
    main_entries = [_entry("a", title="Main A")]
    additional = [_entry("a", title="Additional A"), _entry("b")]

    merged = merge(main_entries, additional)

    assert [e.name for e in merged] == ["a", "b"]
    # main's version of "a" wins, not additional's
    assert merged[0].title == "Main A"


def test_merge_empty_additional_returns_main_unchanged():
    main_entries = [_entry("a")]
    merged = merge(main_entries, [])
    assert merged == main_entries


def test_merge_empty_main_adds_all_additional():
    additional = [_entry("a"), _entry("b")]
    merged = merge([], additional)
    assert [e.name for e in merged] == ["a", "b"]


def test_merge_dedupes_within_additional_itself():
    main_entries = []
    additional = [_entry("a", title="First"), _entry("a", title="Second")]
    merged = merge(main_entries, additional)
    assert len(merged) == 1
    assert merged[0].title == "First"


def test_merge_does_not_mutate_inputs():
    main_entries = [_entry("a")]
    additional = [_entry("b")]
    merge(main_entries, additional)
    assert [e.name for e in main_entries] == ["a"]
    assert [e.name for e in additional] == ["b"]
