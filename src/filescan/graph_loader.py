import os
import csv
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union


class GraphLoader:
    """
    Generic in-memory graph loader.

    Works for:
    - Scanner (filesystem graph)
    - AstScanner (semantic graph)

    Supports:
    - Variable edge schema
    - Optional lineno / end_lineno
    - CSV and JSON exports from ScannerBase
    """

    # =====================================================
    # Initialization
    # =====================================================

    def __init__(self):
        self.reset()

    def reset(self):
        # Raw data
        self.nodes: Dict[str, Dict[str, str]] = {}
        self.edges: List[Dict[str, str]] = []

        self.node_schema: List[str] = []
        self.edge_schema: List[str] = []

        # Adjacency
        self.out_edges: Dict[str, List[Dict]] = defaultdict(list)
        self.in_edges: Dict[str, List[Dict]] = defaultdict(list)

        # Semantic indexes (AST only)
        self.by_qname: Dict[str, str] = {}
        self.by_name: Dict[str, List[str]] = defaultdict(list)
        self.symbols_by_file: Dict[str, List[Tuple[int, int, str]]] = defaultdict(list)

    # =====================================================
    # Public API
    # =====================================================

    def load(self, nodes_path: Path, edges_path: Path) -> None:
        self.reset()

        if nodes_path.suffix == ".json":
            self._load_json(nodes_path)
        else:
            self._load_nodes_csv(nodes_path)
            self._load_edges_csv(edges_path)

        self._build_indexes()

    def is_semantic_graph(self) -> bool:
        return "qualified_name" in self.node_schema

    # =====================================================
    # CSV Loading
    # =====================================================

    def _load_nodes_csv(self, path: Path):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)

            # Read header (skip schema comments)
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                self.node_schema = row
                break

            for row in reader:
                if not row:
                    continue
                node_data = dict(zip(self.node_schema, row))
                node_id = node_data["id"]
                self.nodes[node_id] = node_data

    def _load_edges_csv(self, path: Path):
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
                self.edges.append(edge_data)

    # =====================================================
    # JSON Loading (from ScannerBase.to_json)
    # =====================================================

    def _load_json(self, path: Path):
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.node_schema = [x["name"] for x in data["node_schema"]]
        self.edge_schema = [x["name"] for x in data["edge_schema"]]

        for row in data["nodes"]:
            node_data = dict(zip(self.node_schema, row))
            self.nodes[node_data["id"]] = node_data

        for row in data["edges"]:
            edge_data = dict(zip(self.edge_schema, row))
            self.edges.append(edge_data)

    # =====================================================
    # Index Building
    # =====================================================

    def _build_indexes(self):
        for node_id, node in self.nodes.items():
            name = node.get("name")
            qname = node.get("qualified_name")
            module_path = node.get("module_path")
            lineno = node.get("lineno")
            end_lineno = node.get("end_lineno")

            if qname:
                self.by_qname[qname] = node_id

            if name:
                self.by_name[name].append(node_id)

            if module_path and lineno and end_lineno:
                try:
                    start = int(lineno)
                    end = int(end_lineno)
                    self.symbols_by_file[module_path].append(
                        (start, end, node_id)
                    )
                except (ValueError, TypeError):
                    pass

        for edge in self.edges:
            self.out_edges[edge["source"]].append(edge)
            self.in_edges[edge["target"]].append(edge)

        for file in self.symbols_by_file:
            self.symbols_by_file[file].sort(key=lambda x: x[0])

    # =====================================================
    # Semantic Helpers
    # =====================================================

    def find_symbol_at(self, module_path: str, line: int) -> Optional[str]:
        candidates = []

        for start, end, nid in self.symbols_by_file.get(module_path, []):
            if start <= line <= end:
                candidates.append((end - start, nid))

        if not candidates:
            return None

        return min(candidates)[1]

    def extract_node_source(
        self,
        project_root: Union[str, os.PathLike],
        node_id: str,
    ) -> Optional[str]:

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
        except (ValueError, TypeError):
            return None

        if start <= 0 or end < start:
            return None

        root_path = Path(project_root).resolve()
        file_path = root_path / module_path

        if not file_path.is_file():
            return None

        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            return None

        start_idx = start - 1
        end_idx = min(end, len(lines))

        if start_idx >= len(lines):
            return None

        return "".join(lines[start_idx:end_idx])

    def extract_symbol_at(
        self,
        project_root: Union[str, os.PathLike],
        module_path: str,
        line: int,
    ) -> Optional[str]:

        nid = self.find_symbol_at(module_path, line)
        if nid is None:
            return None

        return self.extract_node_source(project_root, nid)