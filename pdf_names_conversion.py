from dataclasses import dataclass
from pathlib import Path, PurePath, PurePosixPath
from typing import ClassVar


def path_linearized_sanitized(pdf_path: str, tmp_path: str = None) -> str:
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


@dataclass(slots=True)
class PdfPath:
    DIR_TMPS: ClassVar[Path] = Path("/tmp/sanitized")
    DIR_TMPM: ClassVar[Path] = Path("/tmp/metadata")
    pdf_path: Path | str

    @classmethod
    def from_pdf_path(cls, pdf_path: Path | str) -> PdfPath:
        cls.DIR_TMPS.mkdir(parents=True, exist_ok=True)
        cls.DIR_TMPM.mkdir(parents=True, exist_ok=True)
        return cls(pdf_path)

    @property
    def path(self) -> Path:
        return Path(self.pdf_path)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def path_base(self) -> Path:
        return self.path.parent

    @property
    def dir_tmp(self) -> Path:
        return self.DIR_TMPS

    @property
    def dir_sanitized(self) -> Path:
        return self.path_base / "sanitized"

    @property
    def path_sanitized_tmp(self) -> Path:
        return self.DIR_TMPS / self.name

    @property
    def path_sanitized(self) -> Path:
        return self.dir_sanitized / self.name
