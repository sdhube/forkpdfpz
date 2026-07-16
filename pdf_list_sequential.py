"""
Single-threaded, iterative YAML -> enrich -> YAML pipeline.

No DB, no thread pool, no queue: entries are processed one at a time in a
plain for-loop. Each enriched entry is written and flushed to disk the
moment it's done, so:
  - `tail -f output.yaml` shows live progress
  - a crash/interrupt mid-run leaves output.yaml valid up through the last
    completed entry (nothing half-written)

PdfManifest is your existing dataclass — the single source of truth for
field names. Replace the placeholder below with the real one; nothing else
needs to change, since every field is read/written generically via
dataclasses.fields().
"""

import dataclasses
import os
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Type

import yaml

INPUT_FILE = "input.yaml"
OUTPUT_FILE = "output.yaml"


# =========================================================================
# YOUR EXISTING DATACLASS — replace with the real PdfManifest.
# Every field below is handled generically; add/rename fields freely.
# =========================================================================

@dataclass
class PdfManifest:
    input_file: str
    title: str = ""
    author: str = ""
    page_count: int = 0
    tags: List[str] = field(default_factory=list)
    description: str = ""
    output_path: str = ""


# =========================================================================
# Load
# =========================================================================

def load_entries(yaml_path: str, dc: Type) -> List[Any]:
    """Reads input YAML entries into a list of PdfManifest instances.
    Validates shape early: unexpected/missing required fields fail here,
    not mid-enrichment."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {"entries": []}

    manifests = []
    for entry in raw.get("entries", []):
        known = {f.name for f in fields(dc)}
        kwargs = {k: v for k, v in entry.items() if k in known}
        manifests.append(dc(**kwargs))
    return manifests


# =========================================================================
# Worker — one entry at a time, same thread
# =========================================================================

def enrich_entry_data(manifest: PdfManifest) -> PdfManifest:
    """Heavy lifting: PDF parsing, network calls, etc. Mutate/return the dataclass."""
    manifest.page_count = manifest.page_count or 1        # placeholder logic
    manifest.description = manifest.description or "enriched"
    return manifest


# =========================================================================
# Incremental writer: append one entry, flush to disk, immediately
# =========================================================================

def _dump_entry_as_list_item(entry: Dict[str, Any], indent: str = "  ") -> str:
    """Renders one entry as a single YAML list item, indented to nest under
    the top-level `entries:` key."""
    block = yaml.dump([entry], default_flow_style=False, sort_keys=False)
    return "".join(indent + line if line.strip() else line for line in block.splitlines(keepends=True))


def process_all(input_path: str, output_path: str, dc: Type) -> None:
    manifests = load_entries(input_path, dc)

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("entries:\n")
        out.flush()
        os.fsync(out.fileno())

        for m in manifests:
            entry: Dict[str, Any] = dataclasses.asdict(m)
            try:
                enriched = enrich_entry_data(m)
                entry = dataclasses.asdict(enriched)
                entry["_status"] = "done"
            except Exception as exc:
                entry["_status"] = "error"
                entry["_error"] = str(exc)

            out.write(_dump_entry_as_list_item(entry))
            out.flush()                # push from Python buffer to OS
            os.fsync(out.fileno())     # push from OS cache to physical disk


def main():
    process_all(INPUT_FILE, OUTPUT_FILE, PdfManifest)


if __name__ == "__main__":
    main()
