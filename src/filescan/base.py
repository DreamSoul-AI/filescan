import os
import csv
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Union, Any
from importlib import resources

# TODO: add concat info to one file
class ScannerBase:
    """
    Base class for graph scanners.

    Design:
    - Canonical keys define logical identity.
    - Node/Edge IDs are truncated SHA1 hashes (16 hex chars).
    - If a collision occurs, deterministic salted rehash is applied.
    - IDs are stable across runs (given deterministic traversal).
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

        # In-memory graph storage
        self._nodes: List[list] = []
        self._edges: List[list] = []

        # Fast lookup indexes
        self._node_index: dict[str, int] = {}
        self._edge_index: dict[str, int] = {}

        # Collision guards
        self._node_key_to_id: dict[str, str] = {}
        self._node_id_to_key: dict[str, str] = {}

        self._edge_key_to_id: dict[str, str] = {}
        self._edge_id_to_key: dict[str, str] = {}

    # =====================================================
    # Reset
    # =====================================================

    def reset(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._node_index.clear()
        self._edge_index.clear()
        self._node_key_to_id.clear()
        self._node_id_to_key.clear()
        self._edge_key_to_id.clear()
        self._edge_id_to_key.clear()

    # =====================================================
    # Hash utilities
    # =====================================================

    @staticmethod
    def _hash16(s: str) -> str:
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

    # =====================================================
    # Node Identity
    # =====================================================

    def _generate_unique_node_id(self, canonical_key: str) -> str:
        """
        Generate collision-safe 16-char hash ID.
        Deterministically salt if collision occurs.
        """
        # Already registered
        existing = self._node_key_to_id.get(canonical_key)
        if existing:
            return existing

        salt = 0

        while True:
            if salt == 0:
                candidate_key = canonical_key
            else:
                candidate_key = f"{canonical_key}#{salt}"

            node_id = self._hash16(candidate_key)
            existing_key = self._node_id_to_key.get(node_id)

            # No collision
            if existing_key is None:
                self._node_id_to_key[node_id] = canonical_key
                self._node_key_to_id[canonical_key] = node_id
                return node_id

            # Same logical node
            if existing_key == canonical_key:
                return node_id

            # Collision → retry
            salt += 1

    # -----------------------------------------------------

    def _add_node(self, row: list) -> str:
        """
        row[0] must be canonical_key.
        ID will be generated safely.
        """
        canonical_key = row[0]
        node_id = self._generate_unique_node_id(canonical_key)

        if node_id in self._node_index:
            return node_id

        row[0] = node_id
        self._node_index[node_id] = len(self._nodes)
        self._nodes.append(row)
        return node_id

    # =====================================================
    # Edge Identity
    # =====================================================

    def _generate_unique_edge_id(
        self,
        source: str,
        target: str,
        relation: str,
        lineno: Optional[int] = None,
    ) -> str:
        canonical_key = f"{source}|{relation}|{target}|{lineno or ''}"

        existing = self._edge_key_to_id.get(canonical_key)
        if existing:
            return existing

        salt = 0

        while True:
            if salt == 0:
                candidate_key = canonical_key
            else:
                candidate_key = f"{canonical_key}#{salt}"

            edge_id = self._hash16(candidate_key)
            existing_key = self._edge_id_to_key.get(edge_id)

            if existing_key is None:
                self._edge_id_to_key[edge_id] = canonical_key
                self._edge_key_to_id[canonical_key] = edge_id
                return edge_id

            if existing_key == canonical_key:
                return edge_id

            salt += 1

    # -----------------------------------------------------

    def _add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        lineno: Optional[int] = None,
        end_lineno: Optional[int] = None,
    ) -> str:
        edge_id = self._generate_unique_edge_id(
            source, target, relation, lineno
        )

        if edge_id in self._edge_index:
            return edge_id

        self._edge_index[edge_id] = len(self._edges)

        row = [edge_id, source, target, relation]

        # Allow extended schemas (e.g. AST scanner)
        if len(self.EDGE_SCHEMA) > 4:
            row.extend([lineno, end_lineno])

        self._edges.append(row)
        return edge_id

    # =====================================================
    # Ignore Handling
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
    # Output Resolution
    # =====================================================

    def _default_output_prefix(self) -> Path:
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
    # CSV Writer
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