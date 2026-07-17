"""
Shared logic used by all three runners:
  - pipeline_sequential.py      (iterative, single thread)
  - pipeline_parallel_threads.py (ThreadPoolExecutor, N workers)
  - pipeline_parallel_async.py   (asyncio Tasks / "promises", N concurrent)

Keeping this in one place means the enrichment logic, YAML load/write, and
PdfManifest schema are defined exactly once — each runner only differs in
*how* it schedules calls to enrich_entry_data, not in what the data looks
like or how it's written to disk.
"""

import dataclasses
import os
import threading
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Type

import yaml


# =========================================================================
# YOUR EXISTING DATACLASS — replace with the real PdfManifest.
# Every field is handled generically via dataclasses.fields(), so adding,
# renaming, or removing fields here needs no other code changes.
# =========================================================================

from PdfManifestEntry import PdfManifestEntry

# =========================================================================
# Load
# =========================================================================

def load_entries(yaml_path: str, dc: Type = PdfManifest) -> List[Any]:
    """Reads input YAML entries into a list of PdfManifest instances.
    Validates shape up front: unknown keys are dropped, missing required
    fields fail here rather than mid-enrichment."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {"entries": []}

    known = {f.name for f in fields(dc)}
    manifests = []
    for entry in raw.get("entries", []):
        kwargs = {k: v for k, v in entry.items() if k in known}
        manifests.append(dc(**kwargs))
    return manifests


# =========================================================================
# Worker — pure function, no I/O side effects, safe to call from any
# thread/task without synchronization.
# =========================================================================

def enrich_entry_data(manifest: PdfManifest) -> PdfManifest:
    """Heavy lifting: PDF parsing, network calls, etc. Mutate/return the dataclass."""
    manifest.page_count = manifest.page_count or 1        # placeholder logic
    manifest.description = manifest.description or "enriched"
    return manifest


def manifest_to_entry_dict(manifest: PdfManifest, status: str, error_msg: str = None) -> Dict[str, Any]:
    entry = dataclasses.asdict(manifest)
    entry["_status"] = status
    if error_msg:
        entry["_error"] = error_msg
    return entry


# =========================================================================
# Incremental append-and-flush writer
# =========================================================================

def dump_entry_as_list_item(entry: Dict[str, Any], indent: str = "  ") -> str:
    """Renders one entry as a single YAML list item, indented to nest under
    the top-level `entries:` key."""
    block = yaml.dump([entry], default_flow_style=False, sort_keys=False)
    return "".join(indent + line if line.strip() else line for line in block.splitlines(keepends=True))


def write_header(out) -> None:
    out.write("entries:\n")
    out.flush()
    os.fsync(out.fileno())


def append_entry(out, entry: Dict[str, Any], write_lock: threading.Lock = None) -> None:
    """Writes one entry and forces it to physical disk immediately.
    Pass write_lock when multiple threads/tasks share the same file handle —
    the GIL does NOT make write()+flush()+fsync() atomic across threads, so
    without a lock, concurrent writers can interleave and corrupt the file."""
    text = dump_entry_as_list_item(entry)

    def _do_write():
        out.write(text)
        out.flush()
        os.fsync(out.fileno())

    if write_lock is not None:
        with write_lock:
            _do_write()
    else:
        _do_write()
