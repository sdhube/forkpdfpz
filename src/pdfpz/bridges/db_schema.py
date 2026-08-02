from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BookOrm(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
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
    book_id = Column(String, default="")
    book_type = Column(String, default="pdf")


# pythonic.sqlalchemy add table with foreignkey
class BookPropsOrm(Base):
    __tablename__ = "books_props"

    # Shared primary key with books: this table's id is both its own
    # primary key and a foreign key into books.id (one row per book).
    id = Column(Integer, ForeignKey("books.id"), primary_key=True)
    orig = Column(Boolean, default=False, nullable=False)
    sanitized = Column(Boolean, default=False, nullable=False)
    # "metadata" is reserved by SQLAlchemy's declarative Base, so the
    # Python attribute is metadata_ while the actual column is "metadata".
    metadata_ = Column("metadata", Boolean, default=False, nullable=False)
    renamed = Column(Boolean, default=False, nullable=False)
    spostscript = Column(Boolean, default=False, nullable=False)
