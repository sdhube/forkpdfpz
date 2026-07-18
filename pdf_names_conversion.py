from pathlib import Path, PurePosixPath


def path_linearized_sanitized(pdf_path: str) -> str:
    p = PurePosixPath(pdf_path)
    out_stem = "".join([p.stem, "-linearized-sanitized"])
    return p.with_stem(out_stem)
 