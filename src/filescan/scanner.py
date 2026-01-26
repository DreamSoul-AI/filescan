import csv
import json
from pathlib import Path
from typing import List, Optional, Any, Union
from .utils import makedir_exist_ok, load_ignore_spec


class Scanner:
    """
    Directory structure scanner that produces a flat, graph-style
    representation of a filesystem tree.

    The scanner walks a directory recursively and emits a list of nodes,
    where each node represents either a file or a directory. Relationships
    are encoded using parent pointers rather than nested structures, making
    the output compact, stable, and easy to post-process.

    Key features
    ------------
    - Recursive directory traversal
    - Flat node list with parent IDs
    - Optional gitignore-style filtering
    - Export to JSON-compatible dict or CSV

    The output format is intentionally designed to be friendly for:
    - programmatic analysis
    - data pipelines (CSV / DataFrame / SQL)
    - LLM ingestion and summarization
    """

    SCHEMA = [
        ("id", "Unique integer ID for this node"),
        ("parent_id", "ID of parent node, or null for root"),
        ("type", "Node type: 'd' = directory, 'f' = file"),
        ("name", "Base name of the file or directory"),
        ("size", "File size in bytes; null for directories"),
    ]

    def __init__(
            self,
            root: Union[str, Path],
            ignore_file: Optional[Union[str, Path]] = None,
    ):
        """
        Create a new Scanner instance.

        Parameters
        ----------
        root : str | pathlib.Path
            Root directory to scan.
        ignore_file : str | pathlib.Path, optional
            Path to a gitignore-style file used to exclude files or
            directories during scanning.
        """
        self.root = Path(root).expanduser().resolve()

        self.ignore_file = (
            Path(ignore_file).expanduser().resolve()
            if ignore_file is not None
            else None
        )

        self._ignore_spec: Optional[Any] = None
        self._nodes: List[list] = []
        self._next_id: int = 0

    # --------
    # public
    # --------

    def scan(self) -> List[list]:
        """
        Scan the directory tree and return the collected node list.

        This method clears any previous scan results, performs a fresh
        recursive traversal starting from the root directory, and
        populates the internal node list.

        Returns
        -------
        list of list
            A flat list of nodes following the schema defined in
            :attr:`SCHEMA`. Each node is represented as a list of values
            in schema order.

        Notes
        -----
        - The scan result is stored internally and reused by export
          methods such as :meth:`to_dict` and :meth:`to_csv`.
        - Calling this method multiple times will re-scan the filesystem.
        """
        self._nodes.clear()
        self._next_id = 0

        if self._ignore_spec is None and self.ignore_file is not None:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        self._walk(self.root, parent_id=None)
        return self._nodes

    def to_dict(self) -> dict:
        """
        Export the scan result as a JSON-serializable dictionary.

        Returns
        -------
        dict
            A dictionary with the following keys:

            - ``root``: string path of the scanned root directory
            - ``schema``: list of field definitions (name + description)
            - ``nodes``: flat list of scanned nodes

        This representation is suitable for:
        - JSON serialization
        - LLM ingestion
        - API responses
        """
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
        """
        Export the scan result as JSON.

        Parameters
        ----------
        output : str | pathlib.Path | None, optional
            Destination path for JSON output.
            If None, write to a default file named after the root directory
            (e.g. <root>.json) in the current working directory.
        indent : int, default=2
            Number of spaces used for JSON indentation.
        ensure_ascii : bool, default=False
            Whether to escape non-ASCII characters.

        Raises
        ------
        RuntimeError
            If called before scan().
        """
        if not self._nodes:
            raise RuntimeError("No scan results available. Call scan() first.")

        data = self.to_dict()

        path = (
            self._default_output_path(".json")
            if output is None
            else Path(output)
        )

        makedir_exist_ok(path)

        with path.open("w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=indent,
                ensure_ascii=ensure_ascii,
            )
        return

    def to_csv(
            self,
            output: Optional[Union[str, Path]] = None,
            *,
            include_schema_comment: bool = True,
    ):
        """
        Write the scan result to a CSV file.

        Parameters
        ----------
        output : str | pathlib.Path | None, optional
            Destination path for CSV output.
            If None, write to a default file named after the root directory
            (e.g. <root>.csv) in the current working directory.
        include_schema_comment : bool, default=True
            If True, prepend schema descriptions as commented rows at
            the top of the CSV file.

        Raises
        ------
        RuntimeError
            If called before scan().
        """
        if not self._nodes:
            raise RuntimeError("No scan results available. Call scan() first.")

        path = (
            self._default_output_path(".csv")
            if output is None
            else Path(output)
        )

        makedir_exist_ok(path)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if include_schema_comment:
                for name, desc in self.SCHEMA:
                    f.write(f"# {name}: {desc}\n")

            writer.writerow([name for name, _ in self.SCHEMA])
            writer.writerows(self._nodes)
        return

    # ----------------
    # internal logic
    # ----------------

    def _default_output_path(self, suffix: str) -> Path:
        name = self.root.name or self.root.resolve().stem or "root"
        return Path.cwd() / f"{name}{suffix}"

    def _is_ignored(self, path: Path) -> bool:
        if self._ignore_spec is None:
            return False
        rel = path.relative_to(self.root)
        return self._ignore_spec.match_file(str(rel))

    def _next_node_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def _walk(self, path: Path, parent_id: Optional[int]):
        if parent_id is not None and self._is_ignored(path):
            return

        node_id = self._next_node_id()
        is_dir = path.is_dir()
        size = None

        if not is_dir:
            try:
                size = path.stat().st_size
            except OSError:
                pass

        self._nodes.append([
            node_id,
            parent_id,
            "d" if is_dir else "f",
            path.name,
            size,
        ])

        if not is_dir:
            return

        try:
            children = sorted(
                path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except OSError:
            return

        for child in children:
            self._walk(child, parent_id=node_id)
        return
