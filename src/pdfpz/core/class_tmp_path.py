from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, Dict


@dataclass(slots=True)
class TmpPath:
    DIR_TMP_MAP: ClassVar[Dict[str, Path]] = {
        "orig": Path("/tmp/tmp_meta/orig"),
        "sanitized": Path("/tmp/tmp_meta/sanitized"),
        "metadata": Path("/tmp/tmp_meta/metadata"),
        "no_info": Path("/tmp/tmp_meta/no_info"),
        "renamed": Path("/tmp/tmp_meta/renamed"),
    }
    pdf_path: Path | str

    @classmethod
    def from_pdf_path(cls, pdf_path: Path | str) -> "TmpPath":
        # ensure all runtime tmp dirs exist
        for d in cls.DIR_TMP_MAP.values():
            d.mkdir(parents=True, exist_ok=True)
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
        return self.DIR_TMP_MAP["sanitized"]

    @property
    def dir_no_info(self) -> Path:
        return self.DIR_TMP_MAP["no_info"]

    @property
    def dir_sanitized(self) -> Path:
        return self.path_base / "sanitized"

    @property
    def path_sanitized_tmp(self) -> Path:
        return self.DIR_TMP_MAP["sanitized"] / self.name

    @property
    def path_sanitized_info_tmp(self) -> Path:
        return self.DIR_TMP_MAP["metadata"] / self.name

    @property
    def path_sanitized_no_info(self) -> Path:
        return self.DIR_TMP_MAP["no_info"] / self.name

    @property
    def path_sanitized_renamed_tmp(self) -> Path:
        return self.DIR_TMP_MAP["renamed"] / self.name

    @property
    def path_sanitized(self) -> Path:
        return self.dir_sanitized / self.name
