import os
import csv
import json
from pathlib import Path
from typing import List, Optional, Union, Any
from importlib import resources
from .utils import simple_decorator


@simple_decorator
def decorated_function():
    return "Hello"


class ScannerBase:
    """
    Base class for graph scanners.

    Design:
    - Node IDs are string-based and provided by subclasses.
    - Edge IDs are deterministically derived from (source, relation, target).
    - No incremental counters are used.
    """

    NODE_SCHEMA: List[tuple] = []

    EDGE_SCHEMA: List[tuple] = [
        ("id", "Unique edge ID"),
        ("source", "Source node ID"),
        ("target", "Target node ID"),
        ("relation", "Edge relation type"),
    ]

    DEFAULT_IGNORE_PATH = resources.files("filescan").joinpath("default.fscanignore")
    OUTPUT_INFIX = ""

    # =====================================================
    # Initialization
    # =====================================================

    def __init__(
        self,
        root: Union[str, Path, List[Union[str, Path]]],
        ignore_file: Optional[Union[str, Path]] = None,
        output: Optional[Union[str, Path]] = None,
    ):
        if isinstance(root, (str, Path)):
            roots = [root]
        else:
            roots = root

        self.root: List[Path] = [
            Path(r).expanduser().resolve() for r in roots
        ]

        self.ignore_file = (
            Path(ignore_file).expanduser().resolve()
            if ignore_file is not None
            else Path(self.DEFAULT_IGNORE_PATH)
        )

        self.output = (
            Path(output).expanduser().resolve()
            if output is not None
            else None
        )

        self._ignore_spec: Optional[Any] = None

        # In-memory graph
        self._nodes: List[list] = []
        self._edges: List[list] = []

    # =====================================================
    # Core mechanics
    # =====================================================

    def reset(self) -> None:
        """Clear in-memory graph."""
        self._nodes.clear()
        self._edges.clear()

    # -----------------------------------------------------

    def _add_node(self, row: list) -> str:
        """
        Add a node row.

        Assumes:
        row[0] is the node ID (string).
        """
        node_id = row[0]
        self._nodes.append(row)
        return node_id

    # -----------------------------------------------------

    def _add_edge(self, edge_id: str, source: str, target: str, relation: str) -> str:
        """
        Add an edge row to the graph.

        Subclasses must generate edge_id.
        """
        self._edges.append([edge_id, source, target, relation])
        return edge_id

    # =====================================================
    # Ignore handling
    # =====================================================

    def _is_ignored(self, path: Path) -> bool:
        if self._ignore_spec is None:
            return False

        for root in self.root:
            try:
                rel = path.relative_to(root)
                break
            except ValueError:
                continue
        else:
            return False

        rel_str = os.path.normpath(str(rel))

        if path.is_dir():
            rel_str = rel_str + os.sep

        rel_str = rel_str.replace(os.sep, "/")

        return bool(self._ignore_spec.match_file(rel_str))

    # =====================================================
    # Output resolution
    # =====================================================

    def _default_output_prefix(self) -> Path:
        """
        Generate default output prefix.
        Handles multiple roots safely.
        """
        if len(self.root) == 1:
            name = self.root[0].name or "root"
        else:
            name = "_".join(r.name or "root" for r in self.root)

        if self.OUTPUT_INFIX:
            name = f"{name}_{self.OUTPUT_INFIX}"

        return Path.cwd() / name

    # -----------------------------------------------------

    def _resolve_prefix(
        self,
        output: Optional[Union[str, Path]],
    ) -> Path:

        if output is not None:
            base = Path(output)
        elif self.output is not None:
            base = self.output
        else:
            return self._default_output_prefix()

        if base.exists() and base.is_dir():
            if len(self.root) == 1:
                return base / (self.root[0].name or "root")
            return base / "_".join(r.name or "root" for r in self.root)

        return base.with_suffix("")

    # =====================================================
    # Export
    # =====================================================

    def to_csv(
        self,
        output: Optional[Union[str, Path]] = None,
        *,
        include_schema_comment: bool = True,
    ) -> None:

        if not self._nodes:
            raise RuntimeError("No scan results available. Call scan() first.")

        prefix = self._resolve_prefix(output)

        nodes_path = prefix.with_name(prefix.name + "_nodes.csv")
        edges_path = prefix.with_name(prefix.name + "_edges.csv")

        nodes_path.parent.mkdir(parents=True, exist_ok=True)

        self._write_csv(
            nodes_path,
            self.NODE_SCHEMA,
            self._nodes,
            include_schema_comment,
        )

        self._write_csv(
            edges_path,
            self.EDGE_SCHEMA,
            self._edges,
            include_schema_comment,
        )

    # -----------------------------------------------------

    def to_json(self, output: Optional[Union[str, Path]] = None) -> None:
        if not self._nodes:
            raise RuntimeError("No scan results available. Call scan() first.")

        prefix = self._resolve_prefix(output)
        path = prefix.with_name(prefix.name + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "root": [str(r) for r in self.root],
            "node_schema": [
                {"name": name, "description": desc}
                for name, desc in self.NODE_SCHEMA
            ],
            "edge_schema": [
                {"name": name, "description": desc}
                for name, desc in self.EDGE_SCHEMA
            ],
            "nodes": self._nodes,
            "edges": self._edges,
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # =====================================================
    # CSV writer
    # =====================================================

    @staticmethod
    def _write_csv(
        path: Path,
        schema: List[tuple],
        rows: List[list],
        include_schema_comment: bool,
    ) -> None:

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if include_schema_comment:
                for name, desc in schema:
                    f.write(f"# {name}: {desc}\n")

            writer.writerow([name for name, _ in schema])
            writer.writerows(rows)