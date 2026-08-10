from sqlalchemy import inspect, or_, text, select

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

# Maps a BooksViewPropsOrm row field name to the TmpPath property whose existence on disk
# determines that field's value. Extend both this and
# map_prop_field_name_to_prop_field together to track another stage.
map_prop_field_to_tmppath_property = {
    "sanitized": "path_sanitized_tmp",
}

map_prop_field_to_tmppath_property_by_norm = {
    "ps": "path_sanitized_ps_tmp",
    "renamed": "path_sanitized_renamed_tmp",
}

# Maps the same key used above to attribute it sets. Kept as a
# separate dict (rather than assuming the names always match) since not
# every BookView2PropsOrm field name lines up with its TmpPath property name.
map_prop_field_name_to_prop_field = {
    "ps": "ps",
    "renamed": "renamed",
    "sanitized": "sanitized",
}


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
        """Set each mapped BookPropsOrm flag by checking whether that stage's
        tmp file exists on disk for this book."""
        tmp_path = TmpPath.from_pdf_path(self.name)
        logger.info(f"name={self.name}")
        fpath = None
        for prop_name, tmppath_property_name in map_prop_field_to_tmppath_property.items():
            fpath = getattr(tmp_path, tmppath_property_name)
            file_exists = is_file(fpath)
            logger.info(
                f"fpath={fpath} file_exist={file_exists} tmp_path={tmp_path} tmp_path_property_name={tmppath_property_name} "
            )
            setattr(self.book_row, map_prop_field_name_to_prop_field[prop_name], file_exists)
        tmp_path = TmpPath.from_pdf_path(self.norm_name)
        for prop_name, tmppath_property_name in map_prop_field_to_tmppath_property_by_norm.items():
            fpath = getattr(tmp_path, tmppath_property_name)
            file_exists = is_file(fpath)
            logger.info(
                f"fpath={fpath} file_exist={file_exists} tmp_path={tmp_path} tmp_path_property_name={tmppath_property_name} "
            )
            setattr(self.book_row, map_prop_field_name_to_prop_field[prop_name], file_exists)
            if prop_name == "renamed" and self.book_row.renamed:
                self.book_row.sz_renamed = get_size(fpath)
                logger.info(f"{fpath} set sz_renamed {self.book_row.sz_renamed}")
            if prop_name == "ps" and self.book_row.ps:
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
                book.ratio_ps_renamed = book.sz_ps * 100 // book.sz_renamed
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
