from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, String
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
