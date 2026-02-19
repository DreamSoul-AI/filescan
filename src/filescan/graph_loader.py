import os
import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union


class GraphLoader:
    """
    Generic in-memory graph loader.

    Works for:
    - Scanner (filesystem graph)
    - AstScanner (semantic graph)

    Automatically adapts to schema.
    """

    def __init__(self):
        # Raw data
        self.nodes: Dict[int, Dict[str, str]] = {}
        self.edges: List[Dict[str, str]] = []

        self.node_schema: List[str] = []
        self.edge_schema: List[str] = []

        # Adjacency
        self.out_edges: Dict[int, List[Dict]] = defaultdict(list)
        self.in_edges: Dict[int, List[Dict]] = defaultdict(list)

        # Optional semantic indexes
        self.by_qname: Dict[str, int] = {}
        self.by_name: Dict[str, List[int]] = defaultdict(list)
        self.symbols_by_file: Dict[str, List[Tuple[int, int, int]]] = defaultdict(list)

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def load(self, nodes_csv: Path, edges_csv: Path) -> None:
        self._load_nodes(nodes_csv)
        self._load_edges(edges_csv)
        self._build_indexes()

    def is_semantic_graph(self) -> bool:
        return "qualified_name" in self.node_schema

    # -------------------------------------------------
    # CSV Loading
    # -------------------------------------------------

    def _load_nodes(self, path: Path):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)

            # Skip schema comments
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                self.node_schema = row
                break

            for row in reader:
                if not row:
                    continue

                node_data = dict(zip(self.node_schema, row))
                node_id = int(node_data["id"])
                self.nodes[node_id] = node_data

    def _load_edges(self, path: Path):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                self.edge_schema = row
                break

            for row in reader:
                if not row:
                    continue

                edge_data = dict(zip(self.edge_schema, row))
                edge_data["id"] = int(edge_data["id"])
                edge_data["source"] = int(edge_data["source"])
                edge_data["target"] = int(edge_data["target"])

                self.edges.append(edge_data)

    # -------------------------------------------------
    # Index Building
    # -------------------------------------------------

    def _build_indexes(self):
        for node_id, node in self.nodes.items():

            name = node.get("name")
            qname = node.get("qualified_name")
            module_path = node.get("module_path")
            lineno = node.get("lineno")
            end_lineno = node.get("end_lineno")

            # Build semantic indexes only if fields exist
            if qname:
                self.by_qname[qname] = node_id

            if name:
                self.by_name[name].append(node_id)

            if module_path and lineno and end_lineno:
                try:
                    self.symbols_by_file[module_path].append(
                        (int(lineno), int(end_lineno), node_id)
                    )
                except ValueError:
                    pass

        # Build adjacency maps
        for edge in self.edges:
            self.out_edges[edge["source"]].append(edge)
            self.in_edges[edge["target"]].append(edge)

        # Sort file symbol ranges for faster lookup
        for file in self.symbols_by_file:
            self.symbols_by_file[file].sort(key=lambda x: x[0])

    # -------------------------------------------------
    # Semantic Helper
    # -------------------------------------------------

    def find_symbol_at(self, module_path: str, line: int) -> Optional[int]:
        """
        Only meaningful for AST graphs.
        Returns smallest enclosing symbol.
        """
        candidates = []

        for start, end, nid in self.symbols_by_file.get(module_path, []):
            if start <= line <= end:
                candidates.append((end - start, nid))

        if not candidates:
            return None

        return min(candidates)[1]

    def extract_node_source(self, project_root, node_id: int) -> Optional[str]:
        """
        Extract the source code for a node using module_path + lineno/end_lineno.

        Returns:
            The exact text from start line to end line (inclusive), or None if not possible.
        """

        node = self.nodes.get(node_id)
        if not node:
            return None

        module_path = node.get("module_path")
        lineno = node.get("lineno")
        end_lineno = node.get("end_lineno")

        if not module_path or not lineno or not end_lineno:
            return None

        try:
            start = int(lineno)
            end = int(end_lineno)
        except ValueError:
            return None

        if start <= 0 or end < start:
            return None

        # Ensure project_root is OS-native absolute path
        root_path = os.path.abspath(os.fspath(project_root))

        # Join using os.path
        file_path = os.path.abspath(
            os.path.join(root_path, module_path)
        )

        if not os.path.isfile(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            return None

        # Python lineno is 1-based; list index is 0-based
        start_idx = start - 1
        end_idx = min(end, len(lines))  # slicing end is exclusive

        if start_idx >= len(lines):
            return None

        return "".join(lines[start_idx:end_idx])

    def extract_symbol_at(self, project_root: Union[str, os.PathLike], module_path: str, line: int) -> Optional[str]:

        """
        Convenience helper:
        - find_symbol_at(module_path, line)
        - extract_node_source(project_root, node_id)
        """
        nid = self.find_symbol_at(module_path, line)
        if nid is None:
            return None
        return self.extract_node_source(project_root, nid)