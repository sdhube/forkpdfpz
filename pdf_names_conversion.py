from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar


@dataclass(slots=True)
class PdfPath:
    DIR_TMPS: ClassVar[Path] = Path("/tmp/tmp_meta/sanitized")
    DIR_TMPM: ClassVar[Path] = Path("/tmp/tmp_meta/metadata")
    DIR_TMPN: ClassVar[Path] = Path("/tmp/tmp_meta/no_info")
    DIR_TMPR: ClassVar[Path] = Path("/tmp/tmp_meta/renamed")
    pdf_path: Path | str

    @classmethod
    def from_pdf_path(cls, pdf_path: Path | str) -> PdfPath:
        cls.DIR_TMPS.mkdir(parents=True, exist_ok=True)
        cls.DIR_TMPM.mkdir(parents=True, exist_ok=True)
        p = PurePosixPath(pdf_path)
        name = p.name
        return cls(name)

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
    def dir_no_info(self) -> Path:
        return self.DIR_TMPN

    @property
    def dir_sanitized(self) -> Path:
        return self.path_base / "sanitized"

    @property
    def path_sanitized_tmp(self) -> Path:
        return self.DIR_TMPS / self.name

    @property
    def path_sanitized_info_tmp(self) -> Path:
        return self.DIR_TMPM / self.name

    @property
    def path_sanitized_no_info(self) -> Path:
        return self.DIR_TMPM / self.name

    @property
    def path_sanitized_renamed(self) -> Path:
        return self.DIR_TMPR / self.name

    @property
    def path_sanitized(self) -> Path:
        return self.dir_sanitized / self.name
