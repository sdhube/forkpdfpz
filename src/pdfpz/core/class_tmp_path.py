from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath


# TmpStage binds each pipeline stage's tmp directory to a single enum
# member (the member name is the stage name itself), replacing
# DIR_TMP_MAP -- a dict whose string keys were repeated, by hand, in
# every path_*_tmp property below. A typo'd key now fails at
# TmpStage.<typo> (AttributeError, at the call site itself) instead of
# DIR_TMP_MAP["<typo>"] (KeyError, only once that property actually runs).
class TmpStage(Enum):
    def __init__(self, dir_path: str) -> None:
        self.dir = Path(dir_path)

    orig = "/tmp/tmp_meta/orig"
    sanitized = "/tmp/tmp_meta/sanitized"
    metadata = "/tmp/tmp_meta/metadata"
    no_info = "/tmp/tmp_meta/no_info"
    renamed = "/tmp/tmp_meta/renamed"
    ps = "/tmp/tmp_meta/ps"
    ps_ratio_size = "/tmp/tmp_meta/ps_ratio_size"
    n_isbn = "/tmp/tmp_meta/n_isbn"


@dataclass(slots=True)
class TmpPath:
    pdf_path: Path | str

    @classmethod
    def from_pdf_path(cls, pdf_path: Path | str) -> "TmpPath":
        # ensure all runtime tmp dirs exist
        for stage in TmpStage:
            stage.dir.mkdir(parents=True, exist_ok=True)
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
        return TmpStage.sanitized.dir

    @property
    def dir_no_info(self) -> Path:
        return TmpStage.no_info.dir

    @property
    def dir_sanitized(self) -> Path:
        return self.path_base / "sanitized"

    @property
    def path_sanitized_tmp(self) -> Path:
        return TmpStage.sanitized.dir / self.name

    @property
    def path_sanitized_info_tmp(self) -> Path:
        return TmpStage.metadata.dir / self.name

    @property
    def path_sanitized_no_info(self) -> Path:
        return TmpStage.no_info.dir / self.name

    @property
    def path_sanitized_renamed_tmp(self) -> Path:
        return TmpStage.renamed.dir / self.name

    @property
    def path_sanitized_ps_tmp(self) -> Path:
        return TmpStage.ps.dir / self.name

    @property
    def path_ps_ratio_size_tmp(self) -> Path:
        return TmpStage.ps_ratio_size.dir / self.name

    @property
    def path_no_isbn(self) -> Path:
        return TmpStage.n_isbn.dir / self.name

    @property
    def path_sanitized(self) -> Path:
        return self.dir_sanitized / self.name
