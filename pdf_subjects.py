
DC = "http://purl.org/dc/elements/1.1/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


def set_xmp_subjects(xmp, subjects):
    if xmp:
        root = etree.fromstring(xmp.encode("utf-8"))
    else:
        root = etree.fromstring(
            f"""<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="{RDF}">
<rdf:Description xmlns:dc="{DC}"/>
</rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>""".encode()
        )

    desc = root.find(".//{%s}Description" % RDF)

    # Remove old dc:subject if it exists
    old = desc.find("{%s}subject" % DC)
    if old is not None:
        desc.remove(old)

    # Create dc:subject/rdf:Bag
    subject = etree.SubElement(desc, "{%s}subject" % DC)
    bag = etree.SubElement(subject, "{%s}Bag" % RDF)

    for item in subjects:
        li = etree.SubElement(bag, "{%s}li" % RDF)
        li.text = item

    return etree.tostring(root, encoding="utf-8", xml_declaration=False).decode("utf-8")


# ---- main ----

doc = fitz.open("input.pdf")

subjects = ["PDF metadata", "Technical document", "Example subject"]

# Legacy /Info metadata
meta = doc.metadata
meta["subject"] = "; ".join(subjects)  # legacy is a single string
doc.set_metadata(meta)

# XMP metadata
xmp = doc.get_xml_metadata()
xmp = set_xmp_subjects(xmp, subjects)
doc.set_xml_metadata(xmp)

doc.save("output.pdf", garbage=4)
doc.close()
