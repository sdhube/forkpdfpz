import fitz
from lxml import etree

from pdf_names_conversion import PdfPath
from pdf_sanitize import save_tmp_mv_on_source


def del_info(p: PdfPath):
    with fitz.open(p.path_sanitized_tmp) as doc:

        # Remove legacy Document Information dictionary
        doc.set_metadata({})

        # Remove XMP metadata stream
        doc.del_xml_metadata()

        # Save with garbage collection to remove unreferenced objects
        doc.save(
            p.path_sanitized_info,
            garbage=4,
            clean=True,
        )


NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def update_xmp(xmp, title, author):
    root = etree.fromstring(xmp.encode("utf-8"))

    # Find rdf:Description
    desc = root.find(".//rdf:Description", NS)
    if desc is None:
        return xmp

    # Update title
    title_node = desc.find("dc:title", NS)
    if title_node is None:
        title_node = etree.SubElement(desc, "{%s}title" % NS["dc"])
        alt = etree.SubElement(title_node, "{%s}Alt" % NS["rdf"])
        li = etree.SubElement(alt, "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li")
        li.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
    else:
        li = title_node.find(".//rdf:li", NS)

    li.text = title

    # Update author
    creator = desc.find("dc:creator", NS)
    if creator is None:
        creator = etree.SubElement(desc, "{%s}creator" % NS["dc"])
        seq = etree.SubElement(creator, "{%s}Seq" % NS["rdf"])
        li = etree.SubElement(seq, "{%s}li" % NS["rdf"])
    else:
        li = creator.find(".//rdf:li", NS)

    li.text = author

    return etree.tostring(root, encoding="utf-8", xml_declaration=False).decode("utf-8")


def create_xmp(title, author):
    return f"""<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>
<rdf:Alt>
<rdf:li xml:lang="x-default">{title}</rdf:li>
</rdf:Alt>
</dc:title>
<dc:creator>
<rdf:Seq>
<rdf:li>{author}</rdf:li>
</rdf:Seq>
</dc:creator>
</rdf:Description>
</rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""


def pdf_update_metadata(p: PdfPath, ext_meta):
    with fitz.open(p.path_sanitized_info) as doc:

        title = ext_meta.title
        author = ext_meta.author

        # Legacy metadata
        meta = doc.metadata
        meta["title"] = title
        meta["author"] = author
        doc.set_metadata(meta)

        # XMP metadata
        xmp = doc.get_xml_metadata()

        if xmp:
            doc.set_xml_metadata(update_xmp(xmp, title, author))
        else:
            doc.set_xml_metadata(create_xmp(title, author))
        save_tmp_mv_on_source(p.path_sanitized_info)
        doc.save("output.pdf", garbage=4)
