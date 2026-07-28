import pikepdf

from logger import logger
from pdf_actions_file import save_tmp_mv_on_source
from pdf_path import PdfPath
from PdfManifestEntry import MANIFEST_TO_PDF_FIELDS, MANIFEST_TO_XMP_FIELDS, PDFSAN_XMP_PREFIX

# Custom XMP namespace for application-specific fields that have no
# standard dc:/pdf:/xmp: equivalent (e.g. info_file). Must be registered
# before the "pdfsan:" prefix can be used as an XMP metadata key.
PDFSAN_XMP_NS = "https://ns.example.org/pdf-sanitizer/1.0/"
pikepdf.models.PdfMetadata.register_xml_namespace(PDFSAN_XMP_NS, PDFSAN_XMP_PREFIX)


def del_info(p: PdfPath):
    with pikepdf.open(p.path_sanitized_tmp) as doc:
        # Remove legacy Document Information dictionary
        # NOTE: newer pikepdf requires /Info to be an indirect object, so a
        # bare pikepdf.Dictionary() can no longer be assigned directly.
        doc.docinfo = doc.make_indirect(pikepdf.Dictionary())

        # Remove XMP metadata stream
        # NOTE: pikepdf.Pdf no longer exposes `.catalog`; use `.Root` instead.
        if "/Metadata" in doc.Root:
            del doc.Root.Metadata

        # Save with compression to remove unreferenced objects
        logger.info(f"saving pdf no info {p.path_sanitized_info_tmp}")
        doc.save(
            p.path_sanitized_info_tmp,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )


# ----------------------------------------------------------------------------
# public functions
# ----------------------------------------------------------------------------


def pdf_update_metadata(p: PdfPath, ext_meta):
    """Update PDF metadata with all matching fields from PdfManifestEntry.

    Args:
        p: PdfPath object with file paths
        ext_meta: PdfManifestEntry object with metadata to apply
    """
    with pikepdf.open(p.path_sanitized_info_tmp) as doc:
        # Build metadata dictionary from manifest fields
        metadata_dict = {}
        for field_name in ["title", "author", "isbn", "year", "name", "input_file"]:
            value = getattr(ext_meta, field_name, "")
            if value:
                metadata_dict[field_name] = value

        # Update legacy Document Information Dictionary with all matching fields
        # (accessing doc.docinfo auto-creates a proper indirect empty dict
        # if one doesn't already exist, so no make_indirect() needed here)
        for field_name, pdf_key in MANIFEST_TO_PDF_FIELDS.items():
            if field_name in metadata_dict:
                doc.docinfo[pdf_key] = metadata_dict[field_name]
            else:
                doc.docinfo[pdf_key] = ""

        # Update XMP metadata via pikepdf's native dict-like interface.
        # open_metadata() returns a PdfMetadata mapping (there is no
        # update_from_string()/whole-document XMP replace in current
        # pikepdf). update_docinfo=False keeps this block from re-touching
        # docinfo, since we already set the (repurposed) legacy fields above
        # and don't want pikepdf's built-in autosync pairing to overwrite
        # them with its own standard mapping.
        with doc.open_metadata(update_docinfo=False) as meta:
            for field_name, xmp_key in MANIFEST_TO_XMP_FIELDS.items():
                value = metadata_dict.get(field_name)
                if value:
                    if field_name == "author":
                        meta[xmp_key] = [value]  # dc:creator is an rdf:Seq
                    else:
                        meta[xmp_key] = value
                elif xmp_key in meta:
                    del meta[xmp_key]

        logger.info(f"saving pdf clean updated info {p.path_sanitized_info_tmp}")
        save_tmp_mv_on_source(
            doc,
            p.path_sanitized_info_tmp,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )
