# purpose (oneline):

Persist `BookOperationState` across separate `pdfpz` invocations, so a
crash or `FAILED` stage partway through a run can actually be resumed
-- and, for stages that touch every book individually, record which
specific books succeeded or failed rather than only the stage's
overall outcome.

# advanteges (oneline):

One state machine (`OperationStateOrm`) that `next_stage`/`is_finished`/
resume always read the same way for all 11 stages, regardless of
whether that row's status was written directly or computed from
per-book detail -- callers never special-case which kind of stage
they're looking at.

# files:

- `src/pdfpz/bridges/db_schema.py` -- `OperationStateOrm`, `BookOperationOrm` (new)
- `src/pdfpz/core/class_book_operations.py` -- `BookOperationState.mark()`/`load_from_db()`, `BookOperationPlan.resume_plan()` (not yet implemented; `run_plan()`'s two in-memory sequences already are)
- `src/pdfpz/actions/class_actions_books.py` -- `BooksActions` methods; which ones loop over books decides which stages get `BookOperationOrm` rows
- `src/pdfpz/bridges/db_schema.py` -- `BookPropsOrm`/`view_books_props` -- existing per-book flags that some looping stages' backfill reads from

Implementation:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/core/class_book_operations.py
sequence:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/Docs/api-cli-hl.md
DB:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/bridges/db_schema.py

# design:
DB schema for saving states:  OperationStateOrm + BookOperationOrm,

 one state machine (OperationStateOrm) that next_stage/is_finished/resume always read, uniformly, for all 11 stages — but it's populated two different ways depending on the stage: computed as an aggregate for the ones that loop, written directly for the ones that don't. BookOperationOrm only exists where there's real per-book work to report, and it's the more detailed table, not a parallel one.

This also resolves the earlier backfill question more cleanly: stages with no loop never get BookOperationOrm rows, so there's no "missing per-book data" to worry about for those four at all — only the looping stages need the backfill-from-books_props treatment I described before.

## Which stages loop, and over what

Whether a `BookOperationStage` gets `BookOperationOrm` rows follows
directly from whether its `BooksActions` method (per `cli.py`'s
`operation_map`) actually iterates `books_collection.books_shelf`/
`books_spines` per book, or just does one thing for the whole
collection:

| Stage | `operation_flag` | `BooksActions` method | Loops per book? |
|---|---|---|---|
| `A_COPY_PDFS` | `copy_pdfs` | `copy_assets_pdf` | Yes -- `books_generator()` |
| `B_UPDATE_ASSETS_INFO` | `update_assets_info` | `update_books_collection_info_and_save` | Yes -- `run_threaded_action(generate_manifest_items(...))` |
| `C_MOVE_NO_INFO` | `move_no_info` | `move_books_to_no_info` | Yes -- `books_generator(has_no_metadata_info)` |
| `D_SANITIZE_DIDIER` | `sanitize_didier` | `sanitize_books_didier` | Yes -- `run_threads_books_collection_pdf_path` |
| `E_FITZ_DIDIER` | `fitz_didier` | `sanitize_books_fitz_didier` | Yes -- `run_threads_books_collection_pdf_path` |
| `F_SANITIZE_INFO` | `sanitize_info` | `sanitize_books_info` | Yes -- `run_threaded_action(generate_manifest_items(...))` |
| `G_SANITIZE_NORMALIZE_NAME` | `sanitize_normalize_name` | `update_normalized_info_and_move_rename_file` | Yes -- `books_generator(...)` |
| `H_LOAD_YAML_EXPORT_DB` | `load_yaml_export_db` | `load_yaml_export_db` | No -- one `export_format("db")` call |
| `I_FILTER_FIRST` | `filter_first` | `filter_first` | No -- reads a single first entry |
| `J_PROPS_FILTER` | `props_filter` | `props_filter` | No, from `BooksActions`' side -- delegates to `BooksPropsAction`, which does its own per-book SQL against `books_props`/`view_books_props` (existing tables), not a Python loop this design needs to duplicate |
| `K_PRINT_FIRST` | `print_first` | `print_first_entry` | No -- reads a single entry |

Seven stages loop (`A`..`G`), four don't (`H`..`K`) -- that's the "four"
the backfill note above refers to. `J_PROPS_FILTER` counts as
non-looping *for this design specifically*: it does touch every book,
but that per-book detail already lives in `books_props`/
`view_books_props`, so duplicating it into `BookOperationOrm` would be
a second copy of the same fact rather than new information.

## `OperationStateOrm` -- the uniform state machine

One row per `(persistence_file_path, stage)`, always exactly 11 rows
per run once that run has started (one per `BookOperationStage`,
`PENDING` until touched) -- this is what `BookOperationState.next_stage`/
`is_finished()`/a future `resume_plan()` read, and the *only* thing
they read; they never look at `BookOperationOrm` directly.

| Column | Type | Notes |
|---|---|---|
| `persistence_file_path` | `String`, PK | identifies the run -- the same path `cli.py` already takes as its one positional argument |
| `stage` | `String`, PK | a `BookOperationStage` member name, e.g. `"C_MOVE_NO_INFO"` |
| `status` | `String` | a `BookOperationStatus` member name: `PENDING`/`RUNNING`/`DONE`/`FAILED`/`SKIPPED` |
| `updated_at` | `DateTime` | last time this row changed |

**How each row gets its `status` -- two different write paths, one read
path:**

- **Non-looping stages (`H`..`K`):** written directly. `BookOperationState.mark(stage, status)`
  upserts this row itself, exactly once per state transition
  (`RUNNING` before the call, `DONE`/`FAILED` after) -- there's only
  ever one outcome to report, so there's nothing to aggregate.
- **Looping stages (`A`..`G`):** computed as an aggregate over that
  stage's `BookOperationOrm` rows, *after* the loop finishes (or, for a
  live in-progress view, on demand):
  - any row `FAILED` -> stage is `FAILED`
  - else any row `RUNNING`/`PENDING` -> stage is `RUNNING`
  - else (every row `DONE`/`SKIPPED`) -> stage is `DONE`

  `BookOperationState.mark(stage, status)` still upserts the
  `OperationStateOrm` row for these stages too -- it's the caller
  (`BooksActions`'s per-book loop, via a small helper) that computes
  *which* status to pass in from the book-level detail, rather than
  `mark()` itself branching on stage type. `mark()`'s own code path
  stays identical for all 11 stages; only what decides the `status`
  argument differs.

Either way, by the time `BookOperationState.load_from_db(persistence_file_path)`
reads this table back, it sees the same shape regardless of which path
populated a given row -- 11 rows, one status each -- so `next_stage`/
`is_finished()` need no per-stage-type branching at all, matching how
they already work today against the in-memory `status` dict.

## `BookOperationOrm` -- per-book detail, looping stages only

One row per `(persistence_file_path, stage, book_id)`, only ever
written for `A_COPY_PDFS`..`G_SANITIZE_NORMALIZE_NAME`. This is what
lets a failure be reported as "12 of 40 books failed sanitize_didier",
not just "sanitize_didier failed" -- and, on `resume_plan()`, lets a
retry skip the 12 that are already `DONE` rather than redoing all 40.

| Column | Type | Notes |
|---|---|---|
| `persistence_file_path` | `String`, PK | same run identifier as `OperationStateOrm` |
| `stage` | `String`, PK | a `BookOperationStage` member name; always one of the seven looping stages |
| `book_id` | `String`, PK, FK -> `books.book_id` | which book this row is about |
| `status` | `String` | a `BookOperationStatus` member name |
| `error_message` | `String`, nullable | populated on `FAILED`, `None` otherwise |
| `updated_at` | `DateTime` | last time this row changed |

Not a table parallel to `OperationStateOrm` -- `OperationStateOrm` is
the single source both kinds of stage report through; `BookOperationOrm`
is strictly *more detail*, feeding `OperationStateOrm`'s aggregate for
the seven stages that have per-book detail to feed it with.

## Backfill: looping stages that overlap `books_props`

Some looping stages (`F_SANITIZE_INFO` most directly, via `sanitize`)
already have a per-book fact recorded in `books_props`/`view_books_props`
(e.g. `sanitized`, `renamed`) from before this design existed. For
those, `BookOperationOrm` rows for *past* runs can be backfilled by
reading the existing `books_props` flag rather than needing a
migration that guesses at history no one recorded: `sanitized == True`
implies `F_SANITIZE_INFO` was `DONE` for that `book_id`, with no new
data collection required. Stages without an existing `books_props`
equivalent (e.g. `A_COPY_PDFS`) simply have no backfill source --
their `BookOperationOrm` history starts from whenever this design
actually ships, same as `OperationStateOrm`'s does for every stage.

Since the four non-looping stages never get `BookOperationOrm` rows at
all (per the table above), there's no backfill question for them
either way -- only the seven looping stages need it, and only some of
those seven have a `books_props` column to backfill from.
