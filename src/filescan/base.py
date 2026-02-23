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
    NODE_SCHEMA: List[tuple] = []
    EDGE_SCHEMA: List[tuple] = [
        ("id", "Unique edge ID"),
        ("source", "Source node ID"),
        ("target", "Target node ID"),
        ("relation", "Edge relation type"),
    ]

    DEFAULT_IGNORE_PATH = resources.files("filescan").joinpath("default.fscanignore")
    OUTPUT_INFIX = ""

    def __init__(
            self,
            # root: Union[str, Path],
            root: Union[str, Path, List[Union[str, Path]]],
            ignore_file: Optional[Union[str, Path]] = None,
            output: Optional[Union[str, Path]] = None,
    ):
        # self.root = Path(root).expanduser().resolve()
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
        self._nodes: List[list] = []
        self._edges: List[list] = []

        self._next_node_id: int = 0
        self._next_edge_id: int = 0

    # =====================================================
    # Core mechanics
    # =====================================================

    def reset(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._next_node_id = 0
        self._next_edge_id = 0

    def _next_node_id_value(self) -> int:
        nid = self._next_node_id
        self._next_node_id += 1
        return nid

    def _next_edge_id_value(self) -> int:
        eid = self._next_edge_id
        self._next_edge_id += 1
        return eid

    def _add_node(self, row: list) -> int:
        self._nodes.append(row)
        return row[0]

    def _add_edge(self, source: int, target: int, relation: str) -> int:
        eid = self._next_edge_id_value()
        self._edges.append([eid, source, target, relation])
        return eid

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

    # def _is_ignored(self, path: Path) -> bool:
    #     if self._ignore_spec is None:
    #         return False
    #
    #     try:
    #         rel = path.relative_to(self.root)
    #     except ValueError:
    #         return False
    #
    #     rel_str = os.path.normpath(str(rel))
    #
    #     if path.is_dir():
    #         rel_str = rel_str + os.sep
    #
    #     rel_str = rel_str.replace(os.sep, "/")
    #
    #     return bool(self._ignore_spec.match_file(rel_str))

    # =====================================================
    # Output resolution
    # =====================================================

    def _default_output_prefix(self) -> Path:
        name = self.root.name or "root"
        if self.OUTPUT_INFIX:
            name = f"{name}_{self.OUTPUT_INFIX}"
        return Path.cwd() / name

    def _resolve_prefix(
            self,
            output: Optional[Union[str, Path]],
    ) -> Path:
        # explicit argument
        if output is not None:
            base = Path(output)
        # constructor-level output
        elif self.output is not None:
            base = self.output
        else:
            return self._default_output_prefix()

        if base.exists() and base.is_dir():
            return base / (self.root.name or "root")

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

    # def to_json(self, output: Optional[Union[str, Path]] = None) -> None:
    #     if not self._nodes:
    #         raise RuntimeError("No scan results available. Call scan() first.")
    #
    #     prefix = self._resolve_prefix(output)
    #     path = prefix.with_name(prefix.name + ".json")
    #     path.parent.mkdir(parents=True, exist_ok=True)
    #
    #     data = {
    #         "root": str(self.root),
    #         "node_schema": [
    #             {"name": name, "description": desc}
    #             for name, desc in self.NODE_SCHEMA
    #         ],
    #         "edge_schema": [
    #             {"name": name, "description": desc}
    #             for name, desc in self.EDGE_SCHEMA
    #         ],
    #         "nodes": self._nodes,
    #         "edges": self._edges,
    #     }
    #
    #     with path.open("w", encoding="utf-8") as f:
    #         json.dump(data, f, indent=2, ensure_ascii=False)

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
