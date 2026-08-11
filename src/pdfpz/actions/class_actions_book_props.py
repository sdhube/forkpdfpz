import shutil
from enum import Enum

from sqlalchemy import and_, inspect, or_, text, select

from pdfpz.actions.pdf_actions_file import get_size
from pdfpz.actions.class_book_manifest_file_actions import is_file
from pdfpz.bridges.db_bridge import Session, engine
from pdfpz.bridges.db_schema import (
    CREATE_VIEW_BOOKS_PROPS_SQL,
    DROP_VIEW_BOOKS_PROPS_SQL,
    BookOrm,
    BookPropsOrm,
    BookViewPropsOrm,
)
from pdfpz.core.class_book_manifest import BooksShelf, PdfManifestEntry
from pdfpz.core.class_tmp_path import TmpPath
from pdfpz.core.logger import logger


# PropStage binds a prop-tracking stage's TmpPath property name and which
# book name it's checked under (the original name vs. the normalized one)
# together, replacing three separately-maintained dicts that had to be
# kept in sync by hand:
#   map_prop_field_to_tmppath_property         (orig-name stages)
#   map_prop_field_to_tmppath_property_by_norm (norm-name stages)
#   map_prop_field_name_to_prop_field           (was pure identity --
#       every key already equalled its value -- so it's gone entirely;
#       BookPropsOrm's field is just stage.name)
class PropStage(Enum):
    def __init__(self, tmppath_property: str, by_norm_name: bool = True) -> None:
        self.tmppath_property = tmppath_property
        self.by_norm_name = by_norm_name

    sanitized = ("path_sanitized_tmp", False)
    n_isbn_prs = ("path_no_isbn",)
    ps = ("path_sanitized_ps_tmp",)
    ps_and_ratio_size = ("path_ps_ratio_size_tmp",)
    renamed = ("path_sanitized_renamed_tmp",)


# FilterableField binds a view_books_props boolean column's field name
# (the member name itself) to its BookViewPropsOrm attribute name,
# replacing FILTERABLE_FIELDS + view_books_props_field_name_to_orm_attr:
# a member's orm_attr is its own name for every field except "metadata"
# -- "metadata" is reserved by SQLAlchemy's declarative base, so
# BookViewPropsOrm maps that column onto metadata_ instead (see
# db_schema.BookViewPropsOrm).
class FilterableField(Enum):
    def __init__(self, orm_attr: str) -> None:
        self.orm_attr = orm_attr

    orig = "orig"
    sanitized = "sanitized"
    metadata = "metadata_"
    renamed = "renamed"
    ps = "ps"
    ps_and_ratio_size = "ps_and_ratio_size"
    n_isbn_prs = "n_isbn_prs"


class BookPropsActions:
    def __init__(self, book_view_row, book_row):
        if not book_row:
            raise ValueError("book_row should not be None")
        self.book_row = book_row
        self.book_view_row = book_view_row

    @property
    def name(self):
        return self.book_view_row.name

    @property
    def norm_name(self):
        return self.book_row.norm_name

    def set_props_from_filesystem(self) -> None:
        """Set each PropStage's BookPropsOrm flag by checking whether that
        stage's tmp file exists on disk for this book -- under self.name
        for stages checked by original name, self.norm_name for the rest
        (PropStage.by_norm_name)."""
        tmp_path_by_name = TmpPath.from_pdf_path(self.name)
        tmp_path_by_norm = TmpPath.from_pdf_path(self.norm_name)
        logger.info(f"name={self.name}")
        for stage in PropStage:
            tmp_path = tmp_path_by_norm if stage.by_norm_name else tmp_path_by_name
            fpath = getattr(tmp_path, stage.tmppath_property)
            file_exists = is_file(fpath)
            logger.info(f"fpath={fpath} file_exist={file_exists} tmp_path={tmp_path} stage={stage.name} ")
            setattr(self.book_row, stage.name, file_exists)
            if stage.name == "renamed" and self.book_row.renamed:
                self.book_row.sz_renamed = get_size(fpath)
                logger.info(f"{fpath} set sz_renamed {self.book_row.sz_renamed}")
            if stage.name == "ps" and self.book_row.ps:
                self.book_row.sz_ps = get_size(fpath)
                logger.info(f"{fpath} set sz_ps {self.book_row.sz_ps}")


class BooksPropsAction:
    def __init__(self, books_shelf: BooksShelf):
        self.book_shelf = books_shelf
        self.table_name = "books_props"
        self.view_name = "view_books_props"

    def create_view(self):
        """(Re)create view_books_props against the current books_props/books
        tables. Idempotent -- CREATE VIEW IF NOT EXISTS is a no-op if the
        view is already there and still valid."""
        with engine.begin() as connection:
            connection.execute(text(CREATE_VIEW_BOOKS_PROPS_SQL))

    def delete_view(self):
        """delete view_books_props against the current books_props/books"""
        with engine.begin() as connection:
            connection.execute(text(DROP_VIEW_BOOKS_PROPS_SQL))

    def delete_table(self):
        """if table in db does not match schema of books props delete books_props table and create books_props table by the schema,"""
        inspector = inspect(engine)
        if self.table_name not in inspector.get_table_names():
            BookPropsOrm.__table__.create(engine)
            self.create_view()
            return
        existing_columns = {col["name"] for col in inspector.get_columns(self.table_name)}
        expected_columns = {col.name for col in BookPropsOrm.__table__.columns}
        if existing_columns != expected_columns:
            self.delete_view()
            BookPropsOrm.__table__.drop(engine)
            BookPropsOrm.__table__.create(engine)
        # view_books_props reads books_props by column name, so it must be
        # (re)created any time delete_table() runs, not only when the table
        # itself was just created/recreated -- CREATE VIEW IF NOT EXISTS is
        # a no-op when the view is already there and still valid.
        self.create_view()

    def insert_valid_items_to_table(self):
        """use sql table books to filter books and
        insert into table books_props all books that has author or title, fileds applicable are book_id,  input_file          book orig name
        """
        with Session() as session:
            existing_ids = {row[0] for row in session.query(BookPropsOrm.book_id).all()}
            valid_books = (
                session.query(BookOrm).filter(or_(BookOrm.title.isnot(None), BookOrm.author.isnot(None))).all()
            )
            new_rows = [BookPropsOrm(book_id=b.book_id) for b in valid_books if b.book_id not in existing_ids]
            if new_rows:
                session.add_all(new_rows)
                session.commit()

    def update_book_props_one_item(self, book_id="0f5bb01f-4b0e-43b5-adbe-baa1ad9c70f1") -> None:
        """use book_id to update BookPropsOrm row"""

        def set_props_norm_name_by_view(book, book_view):
            if not book.norm_name:
                entry = PdfManifestEntry.from_dict(BookViewPropsOrm.orm_to_dict(book_view))
                book.norm_name = entry.get_normilized_name()

        with Session() as session:
            book_view = session.query(BookViewPropsOrm).filter(BookViewPropsOrm.book_id == book_id).first()
            book = session.query(BookPropsOrm).filter(BookPropsOrm.book_id == book_id).first()

            if book is None:
                return
            if not book.norm_name:
                set_props_norm_name_by_view(book, book_view)
                logger.info(f"book norm_name was set to {book.norm_name}")

                # pythonic sqlalchemy save updated row as update to db
                session.commit()

            props_act = BookPropsActions(book_view, book)
            props_act.set_props_from_filesystem()
            if book.sz_ps and book.sz_renamed:
                book.ratio_ps_vs_renamed = book.sz_ps * 100 // book.sz_renamed
            session.commit()

    def update_all_books_props(self):
        with Session() as session:
            props_ids = set(session.scalars(select(BookPropsOrm.book_id)).all())
        for book_id in props_ids:
            self.update_book_props_one_item(book_id)

    def delete_books_named_like_linearized_sanitized(self):
        with Session() as session:
            book_ids = session.scalars(select(BookOrm.book_id).where(BookOrm.name.like("%linearized-sanitized%"))).all()

            for book_id in book_ids:
                session.query(BookPropsOrm).filter(BookPropsOrm.book_id == book_id).delete(synchronize_session=False)

                # pythonic sqlalchemy delete from db
                session.query(BookOrm).filter(BookOrm.book_id == book_id).delete(synchronize_session=False)

            session.commit()

    def copy_books_ps_with_ratio_and_size(self):
        with Session() as session:
            books_names = session.scalars(
                # pythonic sqlalchemy select with and
                select(BookViewPropsOrm.norm_name).where(
                    BookViewPropsOrm.ratio_ps_vs_renamed > 10,
                    BookViewPropsOrm.ratio_ps_vs_renamed < 200,
                    BookViewPropsOrm.sz_ps < 25 * 1024 * 1024,
                )
            ).all()
            for name in books_names:
                tmp_path: TmpPath = TmpPath(name)
                tmp_ps = tmp_path.path_sanitized_ps_tmp
                tmp_ps_size_ratio = tmp_path.path_ps_ratio_size_tmp
                shutil.copyfile(tmp_ps, tmp_ps_size_ratio)

    def copy_books_ps_with_ratio_to_n_isbn(self):
        """select no isbn books file into path_no_isbn instead of path_ps_ratio_size_tmp."""
        with Session() as session:
            books_names = session.scalars(
                # pythonic sqlalchemy select with and
                select(BookViewPropsOrm.norm_name).where(
                    BookViewPropsOrm.ps_and_ratio_size,
                    or_(BookViewPropsOrm.isbn.is_(None), BookViewPropsOrm.isbn == ""),
                )
            ).all()
            for name in books_names:
                tmp_path: TmpPath = TmpPath(name)
                tmp_ps = tmp_path.path_ps_ratio_size_tmp
                tmp_no_isbn = tmp_path.path_no_isbn
                shutil.copyfile(tmp_ps, tmp_no_isbn)


class BooksPropsView:
    """loading rows from db for ui"""

    # Boolean flags on view_books_props that a caller can filter on -- the
    # same fields the UI's props checkboxes are built from. Derived from
    # FilterableField, which is also where the "metadata" ->
    # BookViewPropsOrm.metadata_ attribute-name override lives now.
    FILTERABLE_FIELDS = tuple(f.name for f in FilterableField)

    # Integer columns on view_books_props a caller can cap with an "at
    # most this value" filter.
    MAX_FILTERABLE_FIELDS = ("ratio_ps_vs_renamed", "sz_ps_mega")

    def __init__(self):
        self.rows = None
        # field name -> True / False / None ("no filter", every field's
        # default) -- one independent tri-state filter per FILTERABLE_FIELDS
        # entry, all AND-ed together in select_rows().

        # pythonic dictionary comprehension
        self.prop_filters = {field_name: None for field_name in self.FILTERABLE_FIELDS}
        # field name -> an int upper bound ("at most this value"), or None
        # ("no filter", the default) -- one per MAX_FILTERABLE_FIELDS entry.
        self.max_filters = {field_name: None for field_name in self.MAX_FILTERABLE_FIELDS}
        # True ("has an author"), False ("no author"), or None ("no
        # filter", the default).
        self.author_filter = None
        # True ("has an isbn"), False ("no isbn"), or None ("no filter",
        # the default).
        self.isbn_filter = None

    def set_prop_filter(self, field_name: str, value) -> None:
        """value is True ("filter if true"), False ("filter if false"), or
        None ("no filter", the default). Raises ValueError for a field name
        outside FILTERABLE_FIELDS rather than silently no-opping."""
        if field_name not in self.prop_filters:
            raise ValueError(f"{field_name!r} is not filterable (expected one of {self.FILTERABLE_FIELDS})")
        self.prop_filters[field_name] = value

    def set_max_filter(self, field_name: str, value) -> None:
        """value is an int upper bound ("at most this value"), or None
        ("no filter", the default). Raises ValueError for a field name
        outside MAX_FILTERABLE_FIELDS rather than silently no-opping."""
        if field_name not in self.max_filters:
            raise ValueError(f"{field_name!r} is not filterable (expected one of {self.MAX_FILTERABLE_FIELDS})")
        self.max_filters[field_name] = value

    def set_author_filter(self, value) -> None:
        """value is True ("has an author"), False ("no author"), or None
        ("no filter", the default). An empty-string author counts as "no
        author", same as a NULL one."""
        self.author_filter = value

    def set_isbn_filter(self, value) -> None:
        """value is True ("filter for an isbn"), False ("filter for no
        isbn"), or None ("no filter", the default). An empty-string isbn
        counts as "no isbn", same as a NULL one."""
        self.isbn_filter = value

    def select_rows(self):
        orm_attr = lambda field_name: getattr(  # noqa: E731  # pythonic suppress linter error on this line
            BookViewPropsOrm, FilterableField[field_name].orm_attr
        )

        # pythonic list comprehension builds "sql where" clauses for Boolean variables
        clauses = [
            orm_attr(field_name) == value for field_name, value in self.prop_filters.items() if value is not None
        ]
        # pythonic add list comprehention for "sql where" max value fileters
        clauses += [
            getattr(BookViewPropsOrm, field_name) <= value
            for field_name, value in self.max_filters.items()
            if value is not None
        ]
        # pythonic add "sql where" clauses for string empty/not empty
        if self.author_filter is True:
            clauses.append(and_(BookViewPropsOrm.author.isnot(None), BookViewPropsOrm.author != ""))
        elif self.author_filter is False:
            clauses.append(or_(BookViewPropsOrm.author.is_(None), BookViewPropsOrm.author == ""))
        if self.isbn_filter is True:
            clauses.append(and_(BookViewPropsOrm.isbn.isnot(None), BookViewPropsOrm.isbn != ""))
        elif self.isbn_filter is False:
            clauses.append(or_(BookViewPropsOrm.isbn.is_(None), BookViewPropsOrm.isbn == ""))
        with Session() as session:
            # pythonic using unpack list of clauses
            self.rows = session.scalars(select(BookViewPropsOrm).where(*clauses)).all()
