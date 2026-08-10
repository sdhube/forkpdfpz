from sqlalchemy import inspect, or_

from pdfpz.actions.class_book_manifest_file_actions import is_file
from pdfpz.bridges.db_bridge import Session, engine
from pdfpz.bridges.db_schema import BookOrm, BookPropsOrm, BookViewPropsOrm
from pdfpz.core.class_book_manifest import BooksShelf, PdfProps
from pdfpz.core.class_tmp_path import TmpPath
from pdfpz.core.logger import logger

# Maps a PdfProps field name to the TmpPath property whose existence on disk
# determines that field's value. Extend both this and
# map_prop_field_name_to_prop_field together to track another stage.
map_prop_field_to_tmppath_property = {
    "sanitized": "path_sanitized_tmp",
    "renamed": "path_sanitized_renamed_tmp",
}

# Maps the same key used above to the PdfProps attribute it sets. Kept as a
# separate dict (rather than assuming the names always match) since not
# every PdfProps field name lines up with its TmpPath property name.
map_prop_field_name_to_prop_field = {
    "sanitized": "sanitized",
    "renamed": "renamed",
}


class BookPropsActions:
    def __init__(self, pdf_props: PdfProps):
        if not pdf_props:
            raise ValueError("pdf_props should not be None")
        self.pdf_props = pdf_props
        self.book_id = pdf_props.book_id
        self.name = pdf_props.name

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
        logger.info(f"name={self.name}")
        for prop_name, tmppath_property_name in map_prop_field_to_tmppath_property.items():
            fpath = getattr(tmp_path, tmppath_property_name)
            file_exists = is_file(fpath)
            logger.info(
                f"fpath={fpath} file_exist={file_exists} tmp_path={tmp_path} tmp_path_property_name={tmppath_property_name} "
            )
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
        self.view_name = "view_books_props"

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
            # TODO implement add view view_books_props

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

    def update_book_props_one_item(self, book_id="0f5bb01f-4b0e-43b5-adbe-baa1ad9c70f1") -> PdfProps:
        """use book_id to init PdfPfops by data from table books to initialize PdfProps"""
        with Session() as session:
            book = session.query(BookViewPropsOrm).filter(BookViewPropsOrm.book_id == book_id).first()
            if book is None:
                return None
            pdf_props = PdfProps(
                book_id=book.book_id,
                input_file=book.input_file,
                name=book.name,
                book_norm_name=book.book_norm_name,
                orig=False,
                sanitized=False,
                metadata=False,
                renamed=False,
                sphostscript=False,
                valid_pdf=True,
                book_input_name="",
            )
            props_act = BookPropsActions(pdf_props=pdf_props)
            props_act.set_props_from_filesystem_and_update_db()

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
