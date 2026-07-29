from urllib.parse import urlparse

import requests

from class_book_manifest import PdfManifestEntry


def google_book_info_by_isbn(isbn: str, entry: PdfManifestEntry):
    response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}", timeout=5)
    if response.status_code != 200:
        return response.status_code

    items = response.json().get("items", [])
    if not items:
        return

    volume_info = items[0].get("volumeInfo", {})

    # python labbda expression ()  to process string or iterable which joined to string
    entry.title = (lambda t: t if isinstance(t, str) else ", ".join(t))(volume_info.get("title"))
    entry.author = ", ".join(volume_info.get("authors", []))


def open_library_book_info_by_isbn(isbn, entry: PdfManifestEntry):
    response = requests.get(f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data", timeout=5)
    if response.status_code != 200:
        return response.status_code

    data = response.json()
    book = data.get(f"ISBN:{isbn}")
    if not book:
        return None

    # python labbda expression ()  to process string or iterable which joined to string
    entry.title = (lambda t: t if isinstance(t, str) else ", ".join(t))(book.get("title"))

    entry.author = ", ".join(author["name"] for author in book.get("authors", []))


def doi_book_info_by_link(doi_url: str, entry: PdfManifestEntry):
    """
    additional fields that entry dont have
    """
    # Extract DOI from URL, e.g. https://doi.org/10.1007/978-3-030-28494-7
    doi = urlparse(doi_url).path.lstrip("/")

    response = requests.get(
        f"https://api.crossref.org/works/{doi}",
        headers={"User-Agent": "doi-metadata-script/1.0 (mailto:your@email.com)"},
        timeout=5,
    )
    if response.status_code != 200:
        return response.status_code

    # python safe getting message from dict
    msg = response.json().get("message", {})
    entry.title = msg.get("title", [""])[0]

    # Build a comma-separated string of combined string (given+family) authors names by
    # iteration over list of authors {given:,family:} values ignoring any empty names.
    # msg { author:[{given: , family: },{given: family:}] }
    entry.author = ", ".join(
        name for a in msg.get("author", []) if (name := f"{a.get('given', '')} {a.get('family', '')}".strip())
    )

    # python next Find the first value of a generator on dictionary msg
    entry.year = str(
        next((msg[f]["date-parts"][0][0] for f in ("published-print", "published-online", "issued") if f in msg), "")
    )

    # python  next+iter gives  first value in a returned list,  default "" of next
    entry.isbn = next(iter(msg.get("ISBN", [])), "")
