# purpose (oneline) :
# advanteges (oneline):

# files:

Implementation:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/core/class_book_operations.py 
sequence:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/Docs/api-cli-hl.md
DB:  https://github.com/sdhube/forkpdfpz/blob/package81/src/pdfpz/bridges/db_schema.py

# design:
DB schema for saving states:  OperationStateOrm + BookOperationOrm,

 one state machine (OperationStateOrm) that next_stage/is_finished/resume always read, uniformly, for all 11 stages — but it's populated two different ways depending on the stage: computed as an aggregate for the ones that loop, written directly for the ones that don't. BookOperationOrm only exists where there's real per-book work to report, and it's the more detailed table, not a parallel one.

This also resolves the earlier backfill question more cleanly: stages with no loop never get BookOperationOrm rows, so there's no "missing per-book data" to worry about for those four at all — only the looping stages need the backfill-from-books_props treatment I described before.
