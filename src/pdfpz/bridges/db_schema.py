from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BookOrm(Base):
    __tablename__ = "books"

    book_id = Column(String, primary_key=True)
    valid_pdf = Column(Boolean, default=False, nullable=False)
    file = Column(String, default="")
    input_file = Column(String, default="")
    title = Column(String, default="")
    author = Column(String, default="")
    size = Column(Integer, default=0)
    optimized = Column(Boolean, default=False, nullable=False)
    year = Column(String, default="")
    isbn = Column(String, default="")
    name = Column(String, unique=True, nullable=False, index=True)
    isbn_normalized = Column(String, default="")
    book_type = Column(String, default="pdf")


# pythonic.sqlalchemy add table with foreignkey
class BookPropsOrm(Base):
    __tablename__ = "books_props"

    # Shared primary key with books: this table's id is both its own
    # primary key and a foreign key into books.id (one row per book).
    book_id = Column(String, ForeignKey("books.book_id"), primary_key=True)
    norm_name = Column(String, default=None, nullable=True)
    orig = Column(Boolean, default=False, nullable=False)
    sanitized = Column(Boolean, default=False, nullable=False)
    # "metadata" is reserved by SQLAlchemy's declarative Base, so the
    # Python attribute is metadata_ while the actual column is "metadata".
    metadata_ = Column("metadata", Boolean, default=False, nullable=False)
    renamed = Column(Boolean, default=False, nullable=False)
    ps = Column(Boolean, default=False, nullable=False)
    ps_ratio_size = Column(Boolean, default=False, nullable=False)
    sz_ps = Column(Integer, default=0, nullable=False)
    sz_renamed = Column(Integer, default=0, nullable=False)
    ratio_ps_renamed = Column(Integer, default=0, nullable=False)


# view_books_props exposes every books_props column alongside the BookOrm
# columns callers need without a join of their own: title, author, year,
# isbn, name, input_file. norm_name match
# norm_name
VIEW_BOOKS_PROPS_NAME = "view_books_props"

CREATE_VIEW_BOOKS_PROPS_SQL = f"""
CREATE VIEW IF NOT EXISTS {VIEW_BOOKS_PROPS_NAME} AS
SELECT
    books_props.book_id AS book_id,
    books_props.norm_name AS norm_name,
    books_props.orig AS orig,
    books_props.sanitized AS sanitized,
    books_props.metadata AS metadata,
    books_props.renamed AS renamed,
    books_props.ps AS ps,
    books_props.ps_ratio_size AS ps_ratio_size,
    books_props.sz_ps AS sz_ps,
    books_props.sz_renamed AS sz_renamed,
    books_props.ratio_ps_renamed AS ratio_ps_renamed,
    books_props.sz_ps / 1024 /1024 AS sz_ps_mega,
    books.title AS title,
    books.author AS author,
    books.year AS year,
    books.isbn AS isbn,
    books.name AS name,
    books.input_file AS input_file
FROM books_props
JOIN books ON books.book_id = books_props.book_id
"""

DROP_VIEW_BOOKS_PROPS_SQL = f"DROP VIEW IF EXISTS {VIEW_BOOKS_PROPS_NAME}"

# view_books_props isn't a table Base.metadata.create_all() can create --
# it only exists once CREATE_VIEW_BOOKS_PROPS_SQL runs against the engine
# (see BooksPropsAction.delete_table()). BookViewPropsOrm is therefore
# mapped on its own declarative base, kept separate from Base, so
# db_bridge.create_db()'s Base.metadata.create_all(engine) never tries to
# CREATE TABLE view_books_props itself.
ViewBase = declarative_base()


class BookViewPropsOrm(ViewBase):
    """Read-only mapping onto the view_books_props SQL view: every
    BookPropsOrm field plus BookOrm::(title, author, year, isbn, name,
    input_file)."""

    __tablename__ = VIEW_BOOKS_PROPS_NAME

    book_id = Column(String, primary_key=True)
    norm_name = Column(String)
    orig = Column(Boolean)
    sanitized = Column(Boolean)
    metadata_ = Column("metadata", Boolean)
    renamed = Column(Boolean)
    ps = Column(Boolean)
    ps_ratio_size = Column(Boolean)
    sz_ps = Column(Integer)
    sz_renamed = Column(Integer)
    ratio_ps_renamed = Column(Integer)
    sz_ps_mega = Column(Integer)
    title = Column(String)
    author = Column(String)
    year = Column(String)
    isbn = Column(String)
    name = Column(String)
    input_file = Column(String)

    @staticmethod
    def orm_to_dict(obj):
        # pythonic sqlschema convert obj from ORM  to dict
        return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
