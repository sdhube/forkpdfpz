from pdfpz.actions.class_book_manifest_file_actions import is_file
from pdfpz.bridges.db_bridge import Session
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
    def __init__(self):
        self.pdf_props = None
        self.name = None
        self.id_book_table = None

    def set_name(self, name: str):
        self.name = name

    def set_id(self) -> None:
        """Look up this book's row id in the books table by name."""
        session = Session()
        try:
            row = session.query(BookOrm.id).filter(BookOrm.name == self.name).first()
        finally:
            session.close()
        self.id_book_table = row[0] if row else None

    def set_props_from_db(self) -> None:
        """Set self.pdf_props from the books/books_props rows for this book.

        valid_pdf/input_file live on the books table; the per-stage flags
        live on books_props (one row per book, sharing its id) -- both are
        needed to build a complete PdfProps.
        """
        self.pdf_props = None
        if self.id_book_table is None:
            return

        session = Session()
        try:
            book = session.query(BookOrm).filter(BookOrm.id == self.id_book_table).first()
            props_row = session.query(BookPropsOrm).filter(BookPropsOrm.id == self.id_book_table).first()
        finally:
            session.close()

        if book is None:
            return

        self.pdf_props = PdfProps(
            valid_pdf=book.valid_pdf,
            input_file=book.input_file,
            orig=props_row.orig if props_row else False,
            sanitized=props_row.sanitized if props_row else False,
            metadata=props_row.metadata_ if props_row else False,
            renamed=props_row.renamed if props_row else False,
            sphostscript=props_row.spostscript if props_row else False,
        )

    def save_props_to_db(self) -> None:
        """Upsert this book's books_props row from self.pdf_props."""
        if self.id_book_table is None or self.pdf_props is None:
            return

        session = Session()
        try:
            row = session.query(BookPropsOrm).filter(BookPropsOrm.id == self.id_book_table).first()
            if row is None:
                row = BookPropsOrm(id=self.id_book_table)
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
        if self.pdf_props is None:
            self.pdf_props = PdfProps(
                valid_pdf=False,
                input_file="",
                orig=False,
                sanitized=False,
                metadata=False,
                renamed=False,
                sphostscript=False,
            )
        tmp_path = TmpPath.from_pdf_path(self.name)
        for prop_name, tmppath_property_name in map_prop_field_to_tmppath_property.items():
            fpath = getattr(tmp_path, tmppath_property_name)
            file_exists = is_file(fpath)
            setattr(self.pdf_props, map_prop_field_name_to_prop_field[prop_name], file_exists)

    def set_props_from_filesystem_and_update_db(self) -> None:
        self.set_props_from_filesystem()
        self.save_props_to_db()


class BooksPropsAction:
    def __init__(self, books_shelf: BooksShelf):
        self.book_shelf = books_shelf

    def update_all_props(self) -> None:
        """For every book on the shelf: resolve its DB id, load whatever
        props already exist for it, refresh the filesystem-derived flags,
        and write the result back to books_props."""
        for book in self.book_shelf.books_generator(None):
            props_act = BookPropsActions()
            props_act.set_name(book.name)
            props_act.set_id()
            props_act.set_props_from_db()
            props_act.set_props_from_filesystem_and_update_db()
