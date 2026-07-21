import requests
from urllib.parse import urlparse

from PdfManifestEntry import PdfManifestEntry


def google_book_info_by_isbn(isbn: str, entry: PdfManifestEntry):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"

    response = requests.get(url, timeout=5)
    if response.status_code != 200:
        return response.status_code
    items = data.get("items", [])
    if not items:
        return

    volume_info = items[0].get("volumeInfo", {})

    entry.title = (volume_info.get("title", ""),)
    if isinstance(entry.title, tuple):
        entry.title = ", ".join(entry.title)

    entry.author = ", ".join(volume_info.get("authors", []))


def open_library_book_info_by_isbn(isbn, entry: PdfManifestEntry):
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"

    response = requests.get(url, timeout=5)
    if response.status_code != 200:
        return response.status_code
    data = response.json()
    book_key = f"ISBN:{isbn}"
    if book_key not in data:
        return None

    book = data[book_key]

    entry.title = (book.get("title"),)
    if isinstance(entry.title, tuple):
        entry.title = ", ".join(entry.title)

    entry.author = ", ".join(author["name"] for author in book.get("authors", []))


def doi_book_info_by_link(doi_url: str, entry: PdfManifestEntry):
    """
    additional fields that entry dont have 
    """

    # Extract DOI from URL
    # Example: https://doi.org/10.1007/978-3-030-28494-7
    doi = urlparse(doi_url).path.lstrip("/")

    response = requests.get(
        f"https://api.crossref.org/works/{doi}",
        headers={
            "User-Agent": "doi-metadata-script/1.0 (mailto:your@email.com)"
        },
        timeout=5,
    )
    if response.status_code != 200:
        return response.status_code

    msg = response.json()["message"]

    entry.title = msg.get("title", [""])[0]

    # Subtitle
    subtitle = msg.get("subtitle", [""])
    subtitle = subtitle[0] if subtitle else ""

    # Authors
    authors = []
    for author in msg.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        name = f"{given} {family}".strip()

        if name:
            authors.append(name)
    entry.author=", ".join(authors)
    year = ""
    for field in ("published-print", "published-online", "issued"):
        if field in msg:
            year = msg[field]["date-parts"][0][0]
            break
    entry.year = str(year)
    isbn = msg.get("ISBN", [])
    entry.isbn = isbn[0] if isbn else ""

    publisher = msg.get("publisher", "")
    subjects = msg.get("subject", [])
    item_type = msg.get("type", "")
    abstract = msg.get("abstract", "")
