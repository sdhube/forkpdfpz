import yaml

from pdfpz.core.assets import Asset


class AssetsYaml(Asset):
    """A YAML-backed asset.

    Construct with the document(s) to save: a single positional argument
    (a dict or list) is written as one plain YAML document; more than one
    is written as a `---`-separated document stream (the manifest's
    [{"input_path": ...}, [books...]] shape).

    `load()` always returns the list of documents found in the file (one
    entry for a plain single-document file) -- it doesn't guess at the
    caller's intended shape, since that differs between callers.
    """

    def load(self, path: str) -> list:
        with open(path, "r", encoding="utf-8") as f:
            self.assets = list(yaml.safe_load_all(f))
        return self.assets

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            if len(self.assets) == 1:
                yaml.safe_dump(self.assets[0], f, sort_keys=False, allow_unicode=True)
            else:
                yaml.safe_dump_all(self.assets, f, sort_keys=False, allow_unicode=True, explicit_start=True)
