import csv
import json
from pathlib import Path
from typing import List, Optional, Union, Any


class ScannerBase:
    SCHEMA: List[tuple] = []

    def __init__(
            self,
            root: Union[str, Path],
            ignore_file: Optional[Union[str, Path]] = None,
            output: Optional[Union[str, Path]] = None,
    ):
        self.root = Path(root).expanduser().resolve()

        self.ignore_file = (
            Path(ignore_file).expanduser().resolve()
            if ignore_file is not None
            else None
        )

        self.output = (
            Path(output).expanduser().resolve()
            if output is not None
            else None
        )

        self._ignore_spec: Optional[Any] = None
        self._nodes: List[list] = []
        self._next_id: int = 0

    # -------- shared mechanics --------

    def reset(self) -> None:
        self._nodes.clear()
        self._next_id = 0

    def _next_id_value(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def _default_output_path(self, suffix: str) -> Path:
        name = (
                self.root.name
                or self.root.resolve().stem
                or "root"
        )
        return Path.cwd() / f"{name}{suffix}"

    def _resolve_output_path(
            self,
            output: Optional[Union[str, Path]],
            suffix: str,
    ) -> Path:
        """
        Resolve output path with the following priority:

        1. explicit argument to to_*()
        2. instance-level output (from __init__)
        3. auto-generated default
        """
        if output is not None:
            return Path(output)

        if self.output is not None:
            return self.output.with_suffix(suffix)

        return self._default_output_path(suffix)

    def _is_ignored(self, path: Path) -> bool:
        """
        Check whether a filesystem path should be ignored according to
        gitignore-style rules.

        Paths are matched relative to ``self.root``.
        Directories are normalized with a trailing slash to ensure patterns
        like ``__pycache__/`` behave as expected.
        """
        if self._ignore_spec is None:
            return False

        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return False

        rel_str = str(rel).replace("\\", "/")
        if path.is_dir():
            rel_str += "/"

        return bool(self._ignore_spec.match_file(rel_str))

    # -------- exports --------

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "schema": [
                {"name": name, "description": desc}
                for name, desc in self.SCHEMA
            ],
            "nodes": self._nodes,
        }

    def to_json(
            self,
            output: Optional[Union[str, Path]] = None,
            *,
            indent: int = 2,
            ensure_ascii: bool = False,
    ) -> None:
        if not self._nodes:
            raise RuntimeError("No scan results available. Call scan() first.")

        path = self._resolve_output_path(output, ".json")
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(
                self.to_dict(),
                f,
                indent=indent,
                ensure_ascii=ensure_ascii,
            )

    def to_csv(
            self,
            output: Optional[Union[str, Path]] = None,
            *,
            include_schema_comment: bool = True,
    ) -> None:
        if not self._nodes:
            raise RuntimeError("No scan results available. Call scan() first.")

        path = self._resolve_output_path(output, ".csv")
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if include_schema_comment:
                for name, desc in self.SCHEMA:
                    f.write(f"# {name}: {desc}\n")

            writer.writerow([name for name, _ in self.SCHEMA])
            writer.writerows(self._nodes)
