"""
YAML -> SQLite (via SQLAlchemy) -> parallel enrichment -> YAML pipeline.

Design:
- PdfManifest is your existing dataclass — the single source of truth for field
  names/types. Nothing here hardcodes its fields; they're introspected via
  dataclasses.fields() and reflected into SQLAlchemy Columns at import time.
- Add/rename/remove a field on PdfManifest -> the SQLite table and every query
  below picks it up automatically. No manual column list to keep in sync.
- Tracking columns (id, status, error_msg) are added on top of the reflected
  domain fields — they belong to the pipeline, not to PdfManifest itself.
"""

import concurrent.futures
import dataclasses
import json
import os
import queue
import tempfile
import threading
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Type

import yaml
from sqlalchemy import (
    Boolean, Column, Float, Integer, MetaData, String, Table, Text,
    create_engine, event, func, insert, select, update,
)
from sqlalchemy.orm import registry, sessionmaker

DB_PATH = "progress.db"
OUTPUT_FILE = "output.yaml"
ORDER_BY_FIELD = "title"  # falls back to id if PdfManifest has no such field


# =========================================================================
# 1. YOUR EXISTING DATACLASS
#    Replace this with the real PdfManifest — field names/types below are
#    placeholders only, matching the pdf-sanitizer manifest.rs shape.
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
# 2. Reflection: dataclass fields -> SQLAlchemy Columns
# =========================================================================

_PY_TO_SQL = {
    str: String,
    int: Integer,
    float: Float,
    bool: Boolean,
}


def _sql_column_for(f: dataclasses.Field) -> Column:
    """Maps one dataclass field to a Column. Non-scalar types (list/dict/...)
    are stored as JSON-encoded Text; scalars get a native SQLite type."""
    py_type = f.type if isinstance(f.type, type) else str  # tolerate string annotations
    sql_type = _PY_TO_SQL.get(py_type, Text)
    return Column(f.name, sql_type)


def build_manifest_table(dc: Type, metadata: MetaData, tablename: str = "manifest") -> Table:
    """Reflects every field of dataclass `dc` into a Table, plus pipeline
    tracking columns (id, status, error_msg) that aren't part of `dc` itself."""
    domain_columns = [_sql_column_for(f) for f in fields(dc)]
    return Table(
        tablename,
        metadata,
        Column("id", Integer, primary_key=True),   # preserves original YAML order
        *domain_columns,
        Column("status", String, default="pending"),   # pending/processing/done/error
        Column("error_msg", Text, nullable=True),
    )


def _json_fields(dc: Type) -> set:
    """Field names whose values need json.dumps/json.loads round-tripping
    (anything that isn't a plain str/int/float/bool)."""
    return {f.name for f in fields(dc) if f.type not in _PY_TO_SQL}


def manifest_to_row(m: Any, json_field_names: set) -> Dict[str, Any]:
    """dataclass instance -> dict ready for an INSERT/UPDATE (JSON-encodes complex fields)."""
    row = {}
    for f in fields(m):
        val = getattr(m, f.name)
        row[f.name] = json.dumps(val) if f.name in json_field_names else val
    return row


def row_to_manifest(dc: Type, row: Dict[str, Any], json_field_names: set) -> Any:
    """DB row (mapping of column name -> value) -> dataclass instance (JSON-decodes complex fields)."""
    kwargs = {}
    for f in fields(dc):
        val = row[f.name]
        kwargs[f.name] = json.loads(val) if f.name in json_field_names and val is not None else val
    return dc(**kwargs)


# =========================================================================
# 3. Engine / schema setup
# =========================================================================

def make_engine(db_path: str):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_wal(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA journal_mode=WAL;")  # readers don't block on the writer

    return engine


def init_db(engine, dc: Type):
    metadata = MetaData()
    table = build_manifest_table(dc, metadata)
    metadata.create_all(engine)
    return table


# =========================================================================
# 4. Load YAML -> pending rows
# =========================================================================

def load_initial_entries(yaml_path: str, engine, table: Table, dc: Type, json_field_names: set) -> None:
    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {"entries": []}

    with engine.begin() as conn:
        for i, entry in enumerate(raw.get("entries", [])):
            # Build the dataclass first: this validates the YAML entry has the
            # right shape and applies PdfManifest's own defaults for missing keys.
            m = dc(**{f.name: entry[f.name] for f in fields(dc) if f.name in entry})
            row = manifest_to_row(m, json_field_names)
            row["id"] = i
            row["status"] = "pending"
            conn.execute(insert(table).values(**row))


# =========================================================================
# 5. Worker — operates on the dataclass itself, not raw dicts
# =========================================================================

def enrich_entry_data(entry_id: int, manifest: PdfManifest) -> PdfManifest:
    """Heavy lifting: PDF parsing, network calls, etc. Mutate/return the dataclass."""
    manifest.page_count = manifest.page_count or 1        # placeholder logic
    manifest.description = manifest.description or "enriched"
    return manifest


# =========================================================================
# 6. Single DB writer thread
# =========================================================================

def db_writer_worker(engine, table: Table, json_field_names: set,
                      write_queue: "queue.Queue", stop_event: threading.Event):
    with engine.begin() as conn:
        pass  # ensure table exists / connection warmed before loop

    while not (stop_event.is_set() and write_queue.empty()):
        try:
            entry_id, status, manifest, error_msg = write_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        values = {"status": status, "error_msg": error_msg}
        if manifest is not None:
            values.update(manifest_to_row(manifest, json_field_names))

        with engine.begin() as conn:
            conn.execute(update(table).where(table.c.id == entry_id).values(**values))

        write_queue.task_done()


# =========================================================================
# 7. Progress check — safe to call anytime, from any thread
# =========================================================================

def check_progress(engine, table: Table) -> Dict[str, int]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(table.c.status, func.count()).group_by(table.c.status)
        ).all()
    return dict(rows)


# =========================================================================
# 8. Finalize: DB -> YAML, ordered, atomic overwrite
# =========================================================================

def finalize_to_yaml(engine, table: Table, dc: Type, json_field_names: set,
                      output_path: str, order_by_field: str = ORDER_BY_FIELD) -> None:
    order_col = table.c[order_by_field] if order_by_field in table.c else table.c.id
    with engine.connect() as conn:
        rows = conn.execute(select(table).order_by(func.lower(order_col))).mappings().all()

    entries = []
    for row in rows:
        m = row_to_manifest(dc, row, json_field_names)
        entry = dataclasses.asdict(m)
        entry["_status"] = row["status"]
        if row["error_msg"]:
            entry["_error"] = row["error_msg"]
        entries.append(entry)

    dir_name = os.path.dirname(os.path.abspath(output_path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".yaml.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump({"entries": entries}, f, default_flow_style=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, output_path)  # atomic on POSIX and Windows
    except Exception:
        os.remove(tmp_path)
        raise


# =========================================================================
# 9. Main
# =========================================================================

def main(input_yaml: str = "input.yaml"):
    dc = PdfManifest
    json_field_names = _json_fields(dc)

    engine = make_engine(DB_PATH)
    table = init_db(engine, dc)
    load_initial_entries(input_yaml, engine, table, dc, json_field_names)

    write_queue: "queue.Queue" = queue.Queue()
    stop_event = threading.Event()

    writer_thread = threading.Thread(
        target=db_writer_worker, args=(engine, table, json_field_names, write_queue, stop_event)
    )
    writer_thread.start()

    with engine.connect() as conn:
        pending = conn.execute(
            select(table).where(table.c.status == "pending")
        ).mappings().all()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {
                executor.submit(enrich_entry_data, row["id"], row_to_manifest(dc, row, json_field_names)): row["id"]
                for row in pending
            }
            for future in concurrent.futures.as_completed(future_to_id):
                entry_id = future_to_id[future]
                try:
                    enriched = future.result()
                    write_queue.put((entry_id, "done", enriched, None))
                except Exception as exc:
                    write_queue.put((entry_id, "error", None, str(exc)))
    finally:
        # Runs on normal completion, Ctrl+C, or any unhandled exception, so
        # finalize_to_yaml always sees whatever progress made it into the DB.
        stop_event.set()
        writer_thread.join()
        finalize_to_yaml(engine, table, dc, json_field_names, OUTPUT_FILE)


if __name__ == "__main__":
    main()
