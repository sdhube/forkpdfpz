import requests
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
