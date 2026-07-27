import fitz
from lxml import etree

from logger import logger
from pdf_actions_file import save_tmp_mv_on_source
from pdf_names_conversion import PdfPath


def del_info(p: PdfPath):
    with fitz.open(p.path_sanitized_tmp) as doc:
        # Remove legacy Document Information dictionary
        doc.set_metadata({})

        # Remove XMP metadata stream
        doc.del_xml_metadata()

        # Save with garbage collection to remove unreferenced objects
        logger.info(f"saving pdf no info {p.path_sanitized_info_tmp}")
        doc.save(
            p.path_sanitized_info_tmp,
            garbage=4,
            clean=True,
        )


NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
}

# Mapping of PdfManifestEntry fields to PDF metadata keys
# Fields that support string values in both legacy and XMP formats
MANIFEST_TO_PDF_FIELDS = {
    "title": "title",
    "author": "author",
    "isbn": "keywords",
    "year": "creationDate",
}


def update_xmp(xmp, metadata_dict):
    """Update XMP metadata with multiple fields from manifest.

    Args:
        xmp: XMP string to update
        metadata_dict: Dictionary of field_name -> value pairs to set
    """
    root = etree.fromstring(xmp.encode("utf-8"))

    # Find rdf:Description
    desc = root.find(".//rdf:Description", NS)
    if desc is None:
        return xmp

    # Update title (Alt structure)
    if "title" in metadata_dict and metadata_dict["title"]:
        title_node = desc.find("dc:title", NS)
        if title_node is None:
            title_node = etree.SubElement(desc, "{%s}title" % NS["dc"])
            alt = etree.SubElement(title_node, "{%s}Alt" % NS["rdf"])
            li = etree.SubElement(alt, "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li")
            li.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
        else:
            li = title_node.find(".//rdf:li", NS)
        li.text = metadata_dict["title"]

    # Update author/creator (Seq structure)
    if "author" in metadata_dict and metadata_dict["author"]:
        creator = desc.find("dc:creator", NS)
        if creator is None:
            creator = etree.SubElement(desc, "{%s}creator" % NS["dc"])
            seq = etree.SubElement(creator, "{%s}Seq" % NS["rdf"])
            li = etree.SubElement(seq, "{%s}li" % NS["rdf"])
        else:
            li = creator.find(".//rdf:li", NS)
        li.text = metadata_dict["author"]

    # Update ISBN (simple string field)
    if "isbn" in metadata_dict and metadata_dict["isbn"]:
        isbn_node = desc.find("dc:identifier", NS)
        if isbn_node is None:
            isbn_node = etree.SubElement(desc, "{%s}identifier" % NS["dc"])
        isbn_node.text = metadata_dict["isbn"]

    # Update year/date (simple string field)
    if "year" in metadata_dict and metadata_dict["year"]:
        date_node = desc.find("dc:date", NS)
        if date_node is None:
            date_node = etree.SubElement(desc, "{%s}date" % NS["dc"])
        date_node.text = metadata_dict["year"]

    return etree.tostring(root, encoding="utf-8", xml_declaration=False).decode("utf-8")


def create_xmp(metadata_dict):
    """Create new XMP metadata with fields from manifest.

    Args:
        metadata_dict: Dictionary of field_name -> value pairs
    """
    title = metadata_dict.get("title", "")
    author = metadata_dict.get("author", "")
    isbn = metadata_dict.get("isbn", "")
    year = metadata_dict.get("year", "")
    name = metadata_dict.get("name", "")

    xmp = """<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">"""

    if title:
        xmp += f"""
<dc:title>
<rdf:Alt>
<rdf:li xml:lang="x-default">{title}</rdf:li>
</rdf:Alt>
</dc:title>"""

    if author:
        xmp += f"""
<dc:creator>
<rdf:Seq>
<rdf:li>{author}</rdf:li>
</rdf:Seq>
</dc:creator>"""

    if isbn:
        xmp += f"""
<dc:identifier>{isbn}</dc:identifier>"""

    if year:
        xmp += f"""
<dc:date>{year}</dc:date>"""

    if name:
        xmp += f"""
<dc:coverage>{name}</dc:coverage>"""

    xmp += """
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""

    return xmp


# ----------------------------------------------------------------------------
# public functions
# ----------------------------------------------------------------------------


def pdf_update_metadata(p: PdfPath, ext_meta):
    """Update PDF metadata with all matching fields from PdfManifestEntry.

    Args:
        p: PdfPath object with file paths
        ext_meta: PdfManifestEntry object with metadata to apply
    """
    with fitz.open(p.path_sanitized_info_tmp) as doc:
        # Build metadata dictionary from manifest fields
        metadata_dict = {}
        for field_name in ["title", "author", "isbn", "year", "name"]:
            value = getattr(ext_meta, field_name, "")
            if value:
                metadata_dict[field_name] = value

        # Update legacy Document Information Dictionary with all matching fields
        meta = doc.metadata
        for k in MANIFEST_TO_PDF_FIELDS:
            meta[MANIFEST_TO_PDF_FIELDS[k]] = metadata_dict.get(k, "")
        doc.set_metadata(meta)

        # Update XMP metadata
        xmp = doc.get_xml_metadata()

        if xmp:
            doc.set_xml_metadata(update_xmp(xmp, metadata_dict))
        else:
            doc.set_xml_metadata(create_xmp(metadata_dict))
        logger.info(f"saving pdf clean updated info {p.path_sanitized_info_tmp}")
        save_tmp_mv_on_source(doc, p.path_sanitized_info_tmp, garbage=4, clean=True)
