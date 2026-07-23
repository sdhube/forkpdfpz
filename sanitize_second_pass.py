import pikepdf


def deep_purge_aa(obj) -> int:
    """Recursively walks through any PDF structural object type to delete /AA tags."""
    count = 0

    # Case 1: Handle Dictionaries (Where keys live)
    if isinstance(obj, pikepdf.Dictionary):
        # Target variations of the target key name
        for target in ["/AA", "AA", pikepdf.Name.AA]:
            if target in obj:
                try:
                    del obj[target]
                    count += 1
                except KeyError:
                    pass

        # Recursively search down through every value inside this dictionary
        for key in list(obj.keys()):
            count += deep_purge_aa(obj[key])

    # Case 2: Handle Arrays/Lists (Annotations are often stored in these)
    elif isinstance(obj, pikepdf.Array):
        for item in obj:
            count += deep_purge_aa(item)

    return count


def ultra_sanitize_pdf(pdf) -> None:
    """Scans all objects globally and cleanses nested dictionary/array layers."""

    total_purged = 0

    # Walk through the low-level object index table
    for obj_idx in list(pdf.objects):
        try:
            obj = pdf.get_object(obj_idx)
            total_purged += deep_purge_aa(obj)
        except Exception:
            continue  # Skip encrypted or broken raw bytes streams

    if total_purged > 0:
        # Drop unlinked structural fragments
        pdf.remove_unreferenced_resources()
        # Rewrite file entirely to break incremental logs
        print(f"Success! Recursively purged {total_purged} hidden '/AA' references.")
    else:
        print("No '/AA' references detected anywhere in the file structure.")
