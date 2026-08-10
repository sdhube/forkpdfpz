from sqlalchemy import inspect, or_

from pdfpz.actions.class_book_manifest_file_actions import is_file
from pdfpz.bridges.db_bridge import Session, engine
from pdfpz.bridges.db_schema import BookOrm, BookPropsOrm
from pdfpz.core.class_book_manifest import BooksShelf, PdfProps
from pdfpz.core.class_tmp_path import TmpPath

# Maps a PdfProps field name to the TmpPath property whose existence on disk
# determines that field's value. Extend both this and
# map_prop_field_name_to_prop_field together to track another stage.
map_prop_field_to_tmppath_property = {
    "renamed": "path_sanitized_renamed_tmp",
}

# Maps the same key used above to the PdfProps attribute it sets. Kept as a
# separate dict (rather than assuming the names always match) since not
# every PdfProps field name lines up with its TmpPath property name.
map_prop_field_name_to_prop_field = {
    "renamed": "renamed",
}


class BookPropsActions:
    def __init__(self, pdf_props: PdfProps):
        self.pdf_props = pdf_props
        self.book_id = pdf_props.book_id if pdf_props else None
        self.name = ""

    def set_name(self):
        """Set self.name from self.pdf_props' normalized book name."""
        self.name = self.pdf_props.book_norm_name if self.pdf_props else ""

    def save_props_to_db(self) -> None:
        """Upsert this book's books_props row from self.pdf_props."""
        if self.book_id is None or self.pdf_props is None:
            return

        session = Session()
        try:
            row = session.query(BookPropsOrm).filter(BookPropsOrm.book_id == self.book_id).first()
            if row is None:
                row = BookPropsOrm(book_id=self.book_id)
                session.add(row)
            row.orig = self.pdf_props.orig
            row.sanitized = self.pdf_props.sanitized
            row.metadata_ = self.pdf_props.metadata
            row.renamed = self.pdf_props.renamed
            row.spostscript = self.pdf_props.sphostscript
            session.commit()
        finally:
            session.close()

    def set_props_from_filesystem(self) -> None:
        """Set each mapped PdfProps flag by checking whether that stage's
        tmp file exists on disk for this book."""
        tmp_path = TmpPath.from_pdf_path(self.name)
        for prop_name, tmppath_property_name in map_prop_field_to_tmppath_property.items():
            fpath = getattr(tmp_path, tmppath_property_name)
            file_exists = is_file(fpath)
            setattr(self.pdf_props, map_prop_field_name_to_prop_field[prop_name], file_exists)

    def update_db(self):
        # update db table books_props item book_id
        # book_id, input_file are immutable for the item
        # update te mutable fields : orig, sanitizedm metadatam renemed, spostcript
        self.save_props_to_db()

    def set_props_from_filesystem_and_update_db(self) -> None:
        self.set_props_from_filesystem()
        self.update_db()


class BooksPropsAction:
    def __init__(self, books_shelf: BooksShelf):
        self.book_shelf = books_shelf
        self.table_name = "books_props"

    def delete_table(self):
        """if table in db does not match schema of books props delete books_props table and create books_props table by the schema,"""
        inspector = inspect(engine)
        if self.table_name not in inspector.get_table_names():
            BookPropsOrm.__table__.create(engine)
            return
        existing_columns = {col["name"] for col in inspector.get_columns(self.table_name)}
        expected_columns = {col.name for col in BookPropsOrm.__table__.columns}
        if existing_columns != expected_columns:
            BookPropsOrm.__table__.drop(engine)
            BookPropsOrm.__table__.create(engine)

    def insert_valid_items_to_table(self):
        """use sql table books to filter books and
        insert into table books_props all books that has author or title, fileds applicable are book_id,  input_file          book orig name
        """
        with Session() as session:
            existing_ids = {row[0] for row in session.query(BookPropsOrm.book_id).all()}
            valid_books = (
                session.query(BookOrm).filter(or_(BookOrm.title.isnot(None), BookOrm.author.isnot(None))).all()
            )
            new_rows = [
                BookPropsOrm(book_id=b.book_id, input_file=b.input_file, book_norm_name=b.name)
                for b in valid_books
                if b.book_id not in existing_ids
            ]
            if new_rows:
                session.add_all(new_rows)
                session.commit()

    def update_book_props_one_item(self, book_id) -> PdfProps:
        """use book_id to init PdfPfops by data from table books to initialize PdfProps"""
        with Session() as session:
            book = session.query(BookOrm).filter(BookOrm.book_id == book_id).first()
            if book is None:
                return None
            return PdfProps(
                book_id=book.book_id,
                input_file=book.input_file,
                book_norm_name=book.name,
                orig=False,
                sanitized=False,
                metadata=False,
                renamed=False,
                sphostscript=False,
                valid_pdf=book.valid_pdf,
                book_input_name="",
            )

    def update_all_props(self) -> None:
        """For every book on the shelf: resolve its DB id, load whatever
        props already exist for it, refresh the filesystem-derived flags,
        and write the result back to books_props."""
        for book in self.book_shelf.books_generator(None):
            props_act = BookPropsActions()
            props_act.set_name(book.name)
            props_act.set_id(book.book_id)
            props_act.set_props_from_db()
            props_act.set_props_from_filesystem_and_update_db()
