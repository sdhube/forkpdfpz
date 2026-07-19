from pathlib import Path, PurePosixPath, PurePath


def path_linearized_sanitized(pdf_path: str, tmp_path: str) -> str:
    p = PurePosixPath(pdf_path)
    out_stem = "".join([p.stem, "-linearized-sanitized"])
    out = p.with_stem(out_stem)
    out_path_pure = PurePath(str(out))

    name = out_path_pure.name
    out_path = Path(str(out))
    if not out_path.is_file():
        if tmp_path:
            out_path = Path(tmp_path).joinpath(name)
        else:
            out_path = Path(name)
    return str(out_path)
