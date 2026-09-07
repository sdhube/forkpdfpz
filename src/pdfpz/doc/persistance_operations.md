# purpose (oneline):

Persist `BookOperationState` across invocations so a crash/`FAILED`
stage can resume, and record per-book outcomes for stages that touch
every book individually.

# advanteges (oneline):

One state machine (`OperationStateOrm`) that `next_stage`/`is_finished`/
resume always read the same way, whether a row's status was written
directly or computed from per-book detail.

# files:

- `src/pdfpz/bridges/db_schema.py` -- `OperationStateOrm`, `BookOperationOrm` (new)
- `src/pdfpz/core/class_book_operations.py` -- `BookOperationState.mark()`/`load_from_db()`, `BookOperationPlan.resume_plan()` (not yet implemented; `run_plan()` already is)
- `src/pdfpz/actions/class_actions_books.py` -- which methods loop over books decides which stages get `BookOperationOrm` rows
- `src/pdfpz/bridges/db_schema.py` -- `BookPropsOrm`/`view_books_props` -- existing per-book flags some looping stages can backfill from

Implementation:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/core/class_book_operations.py
sequence:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/Docs/api-cli-hl.md
DB:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/bridges/db_schema.py

# design:

`OperationStateOrm` is the one state machine `next_stage`/`is_finished`/
resume always read, for all 8 stages -- populated two ways: computed as
an aggregate for stages that loop over books, written directly for the
ones that don't. `BookOperationOrm` only exists for stages with real
per-book work to report; it's detail, not a parallel table.

Stages with no loop never get `BookOperationOrm` rows, so there's no
missing-data question for those three -- only the five looping stages
need backfill-from-`books_props` treatment.

## Which stages loop

| Stage | Flag | Method | Loops per book? |
|---|---|---|---|
| `A_COPY_PDFS` | `copy_pdfs` | `copy_assets_pdf` | Yes |
| `B_SANITIZE_PIKE` | `sanitize_pike` | `sanitize_books_pike` | Yes -- threaded |
| `D_UPDATE_ASSETS_INFO` | `update_assets_info` | `update_books_collection_info_and_save` | Yes -- threaded |
| `F_SANITIZE_INFO` | `sanitize_info` | `sanitize_books_info` | Yes -- threaded |
| `G_SANITIZE_NORMALIZE_NAME` | `sanitize_normalize_name` | `update_normalized_info_and_move_rename_file` | Yes |
| `H_LOAD_YAML_EXPORT_DB` | `export_books_to_db` | `export_books_to_db` | No -- one `export_format("db")` call |
| `I_PROPS_FILTER` | `props_filter` | `props_filter` | No, from here -- delegates to `BooksPropsAction`'s own SQL against `books_props`, not a loop this design duplicates |
| `K_FILTER_FIRST` | `filter_first` | `filter_first` | No -- reads a single entry |

Five loop (`A`, `B`, `D`, `F`, `G`), three don't (`H`, `I`, `K`).
`I_PROPS_FILTER` counts as non-looping here specifically because its
per-book detail already lives in `books_props`/`view_books_props` --
duplicating it into `BookOperationOrm` would just copy an existing fact.

## `OperationStateOrm` -- the uniform state machine

One row per `(persistence_file_path, stage)`; `next_stage`/
`is_finished()`/resume read only this table, never `BookOperationOrm`.

| Column | Type | Notes |
|---|---|---|
| `persistence_file_path` | `String`, PK | identifies the run |
| `stage` | `String`, PK | a `BookOperationStage` member name |
| `status` | `String` | a `BookOperationStatus` member name |
| `updated_at` | `DateTime` | last change |

- **Non-looping (`H`, `I`, `K`):** `BookOperationState.mark(stage,
  status)` writes the row directly -- one outcome, nothing to aggregate.
- **Looping (`A`, `B`, `D`, `F`, `G`):** the row is a computed aggregate
  over that stage's `BookOperationOrm` rows: any `FAILED` -> `FAILED`;
  else any non-terminal -> `RUNNING`; else `DONE`. `mark()`'s own code
  path is identical either way -- only what decides the `status`
  argument (a per-book loop vs. a single call) differs.

## `BookOperationOrm` -- per-book detail, looping stages only

One row per `(persistence_file_path, stage, book_id)`, only for the
five looping stages -- lets a failure read as "12 of 40 books failed",
not just "stage failed", and lets `resume_plan()` skip already-`DONE`
books on retry.

| Column | Type | Notes |
|---|---|---|
| `persistence_file_path` | `String`, PK | same run identifier |
| `stage` | `String`, PK | one of the five looping stages |
| `book_id` | `String`, PK, FK -> `books.book_id` | which book |
| `status` | `String` | a `BookOperationStatus` member name |
| `error_message` | `String`, nullable | set on `FAILED` |
| `updated_at` | `DateTime` | last change |

## Backfill

`F_SANITIZE_INFO` already has a `books_props` equivalent (`sanitized`)
recorded before this design existed -- `sanitized == True` implies
`F_SANITIZE_INFO` was `DONE` for that book, backfillable with no new
data collection. Stages without an existing `books_props` column (e.g.
`A_COPY_PDFS`) have no backfill source; their history starts once this
design ships. The three non-looping stages never need backfill at all.
