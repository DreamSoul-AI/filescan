import os
import csv
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union

from .scanner import Scanner
from .ast_scanner import AstScanner


# ==============================================================================
# Internal Graph Container
# ==============================================================================

class _Graph:
    """
    Internal container for one graph (filesystem OR AST).
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, str]] = {}
        self.edges: List[Dict[str, str]] = []

        self.node_schema: List[str] = []
        self.edge_schema: List[str] = []

        self.out_edges: Dict[str, List[Dict]] = defaultdict(list)
        self.in_edges: Dict[str, List[Dict]] = defaultdict(list)

        # Semantic-only indexes (used for AST graph)
        self.by_qname: Dict[str, str] = {}
        self.by_name: Dict[str, List[str]] = defaultdict(list)
        self.symbols_by_file: Dict[str, List[Tuple[int, int, str]]] = defaultdict(list)


# ==============================================================================
# GraphBuilder
# ==============================================================================

class GraphBuilder:
    """
    Unified graph manager.

    Capabilities:
    - Build filesystem graph
    - Build AST graph (optional)
    - Load graphs from CSV/JSON
    - Maintain separate graph structures
    - Provide semantic indexing for AST
    """

    # =====================================================
    # Initialization
    # =====================================================

    def __init__(self):
        self.reset()

    def reset(self):
        self.filesystem = _Graph()
        self.ast = _Graph()

    # =====================================================
    # BUILD FROM SOURCE
    # =====================================================

    def build(
        self,
        roots: List[Path],
        ignore_file: Optional[Path] = None,
        *,
        include_filesystem: bool = False,
        include_ast: bool = True,
    ):
        """
        Build graphs directly from source.
        """

        self.reset()

        if include_filesystem:
            fs_scanner = Scanner(roots, ignore_file=ignore_file)
            fs_scanner.scan()
            self._ingest(fs_scanner, self.filesystem)

        if include_ast:
            ast_scanner = AstScanner(roots, ignore_file=ignore_file)
            ast_scanner.scan()
            self._ingest(ast_scanner, self.ast)

        self._build_indexes()
        return self

    def _ingest(self, scanner, graph: _Graph):
        node_schema = [x[0] for x in scanner.NODE_SCHEMA]
        edge_schema = [x[0] for x in scanner.EDGE_SCHEMA]

        graph.node_schema = node_schema
        graph.edge_schema = edge_schema

        for row in scanner._nodes:
            node_data = dict(zip(node_schema, row))
            graph.nodes[node_data["id"]] = node_data

        for row in scanner._edges:
            edge_data = dict(zip(edge_schema, row))
            graph.edges.append(edge_data)

    # =====================================================
    # LOAD EXISTING GRAPH
    # =====================================================

    def load(
        self,
        nodes_path: Path,
        edges_path: Optional[Path] = None,
        *,
        target: str = "ast",  # "ast" or "filesystem"
    ):
        """
        Load graph from CSV or JSON into target graph.
        """

        if target not in ("ast", "filesystem"):
            raise ValueError("target must be 'ast' or 'filesystem'")

        graph = getattr(self, target)
        graph.__init__()  # reset just that graph

        if nodes_path.suffix == ".json":
            self._load_json(nodes_path, graph)
        else:
            self._load_nodes_csv(nodes_path, graph)
            if edges_path:
                self._load_edges_csv(edges_path, graph)

        self._build_indexes()
        return self

    # =====================================================
    # CSV Loading
    # =====================================================

    def _load_nodes_csv(self, path: Path, graph: _Graph):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                graph.node_schema = row
                break

            for row in reader:
                if not row:
                    continue
                node_data = dict(zip(graph.node_schema, row))
                graph.nodes[node_data["id"]] = node_data

    def _load_edges_csv(self, path: Path, graph: _Graph):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                graph.edge_schema = row
                break

            for row in reader:
                if not row:
                    continue
                edge_data = dict(zip(graph.edge_schema, row))
                graph.edges.append(edge_data)

    # =====================================================
    # JSON Loading
    # =====================================================

    def _load_json(self, path: Path, graph: _Graph):
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        graph.node_schema = [x["name"] for x in data["node_schema"]]
        graph.edge_schema = [x["name"] for x in data["edge_schema"]]

        for row in data["nodes"]:
            node_data = dict(zip(graph.node_schema, row))
            graph.nodes[node_data["id"]] = node_data

        for row in data["edges"]:
            edge_data = dict(zip(graph.edge_schema, row))
            graph.edges.append(edge_data)

    # =====================================================
    # INDEX BUILDING
    # =====================================================

    def _build_indexes(self):
        """
        Build adjacency for both graphs.
        Build semantic indexes for AST graph only.
        """

        # ---- adjacency (both graphs) ----
        for graph in (self.filesystem, self.ast):
            graph.out_edges.clear()
            graph.in_edges.clear()

            for edge in graph.edges:
                graph.out_edges[edge["source"]].append(edge)
                graph.in_edges[edge["target"]].append(edge)

        # ---- semantic indexes (AST only) ----
        self.ast.by_qname.clear()
        self.ast.by_name.clear()
        self.ast.symbols_by_file.clear()

        for node_id, node in self.ast.nodes.items():
            name = node.get("name")
            qname = node.get("qualified_name")
            module_path = node.get("module_path")
            lineno = node.get("lineno")
            end_lineno = node.get("end_lineno")

            if qname:
                self.ast.by_qname[qname] = node_id

            if name:
                self.ast.by_name[name].append(node_id)

            if module_path and lineno and end_lineno:
                try:
                    start = int(lineno)
                    end = int(end_lineno)
                    self.ast.symbols_by_file[module_path].append(
                        (start, end, node_id)
                    )
                except (ValueError, TypeError):
                    pass

        for file in self.ast.symbols_by_file:
            self.ast.symbols_by_file[file].sort(key=lambda x: x[0])

    # =====================================================
    # AST Semantic Helpers
    # =====================================================

    def has_ast(self) -> bool:
        return bool(self.ast.nodes)

    def find_symbol_at(self, module_path: str, line: int) -> Optional[str]:
        """
        Return smallest AST symbol containing given line.
        """
        candidates = []

        for start, end, nid in self.ast.symbols_by_file.get(module_path, []):
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

        node = self.ast.nodes.get(node_id)
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

    # =====================================================
    # Context Merge
    # =====================================================

    def export_context_merged(
        self,
        output_path: Union[str, Path],
        *,
        fs_nodes_path: Optional[Path] = None,
        fs_edges_path: Optional[Path] = None,
        ast_nodes_path: Optional[Path] = None,
        ast_edges_path: Optional[Path] = None,
    ) -> None:
        """
        Concatenate filesystem and AST CSV files into ONE file.
        """

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        sections = []

        if fs_nodes_path and fs_edges_path:
            sections.extend([
                ("FILESYSTEM NODES", fs_nodes_path),
                ("FILESYSTEM EDGES", fs_edges_path),
            ])

        if ast_nodes_path and ast_edges_path:
            sections.extend([
                ("AST NODES", ast_nodes_path),
                ("AST EDGES", ast_edges_path),
            ])

        with output_path.open("w", encoding="utf-8") as out:
            for title, path in sections:
                out.write("# " + "=" * 78 + "\n")
                out.write(f"# {title}\n")
                out.write("# " + "=" * 78 + "\n\n")

                if not path.exists():
                    out.write(f"# Missing file: {path}\n\n")
                    continue

                with path.open("r", encoding="utf-8") as f:
                    content = f.read().strip()
                    out.write(content)
                    out.write("\n\n")