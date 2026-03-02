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
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []
        self.edge_ids: set[str] = set()

        # FULL schema: (name, description)
        self.node_schema: List[Tuple[str, str]] = []
        self.edge_schema: List[Tuple[str, str]] = []

        self.out_edges: Dict[str, List[Dict]] = defaultdict(list)
        self.in_edges: Dict[str, List[Dict]] = defaultdict(list)

        # AST semantic indexes
        self.by_qname: Dict[str, str] = {}
        self.by_name: Dict[str, List[str]] = defaultdict(list)
        self.symbols_by_file: Dict[str, List[Tuple[int, int, str]]] = defaultdict(list)


# ==============================================================================
# GraphBuilder
# ==============================================================================

class GraphBuilder:

    def __init__(self):
        self.reset()

    def reset(self):
        self.filesystem = _Graph()
        self.ast = _Graph()

    # =====================================================
    # BUILD
    # =====================================================

    def build(
        self,
        roots: List[Path],
        ignore_file: Optional[Path] = None,
        *,
        include_filesystem: bool = False,
        include_ast: bool = True,
    ):
        self.reset()

        if include_filesystem:
            scanner = Scanner(roots, ignore_file=ignore_file)
            self.filesystem.node_schema = Scanner.NODE_SCHEMA
            self.filesystem.edge_schema = Scanner.EDGE_SCHEMA
            scanner.scan_into(self.filesystem)

        if include_ast:
            scanner = AstScanner(roots, ignore_file=ignore_file)
            self.ast.node_schema = AstScanner.NODE_SCHEMA
            self.ast.edge_schema = AstScanner.EDGE_SCHEMA
            scanner.scan_into(self.ast)

        self._build_indexes()
        return self

    def has_ast(self) -> bool:
        return bool(self.ast.nodes)

    # =====================================================
    # EXPORT
    # =====================================================

    def export_filesystem(self, output_prefix: Union[str, Path]) -> None:
        self._export_graph(self.filesystem, output_prefix)

    def export_ast(self, output_prefix: Union[str, Path]) -> None:
        self._export_graph(self.ast, output_prefix)

    def _export_graph(self, graph: _Graph, output_prefix: Union[str, Path]):

        prefix = Path(output_prefix).with_suffix("")
        prefix.parent.mkdir(parents=True, exist_ok=True)

        nodes_path = prefix.with_name(prefix.name + "_nodes.csv")
        edges_path = prefix.with_name(prefix.name + "_edges.csv")
        json_path = prefix.with_name(prefix.name + ".json")

        # ---- CSV NODES ----
        with nodes_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Write schema comments
            for name, desc in graph.node_schema:
                f.write(f"# {name}: {desc}\n")

            # Header
            writer.writerow([name for name, _ in graph.node_schema])

            # Rows
            for node in graph.nodes.values():
                writer.writerow([node.get(name) for name, _ in graph.node_schema])

        # ---- CSV EDGES ----
        with edges_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            for name, desc in graph.edge_schema:
                f.write(f"# {name}: {desc}\n")

            writer.writerow([name for name, _ in graph.edge_schema])

            for edge in graph.edges:
                writer.writerow([edge.get(name) for name, _ in graph.edge_schema])

        # ---- JSON ----
        data = {
            "node_schema": [
                {"name": name, "description": desc}
                for name, desc in graph.node_schema
            ],
            "edge_schema": [
                {"name": name, "description": desc}
                for name, desc in graph.edge_schema
            ],
            "nodes": [
                [node.get(name) for name, _ in graph.node_schema]
                for node in graph.nodes.values()
            ],
            "edges": [
                [edge.get(name) for name, _ in graph.edge_schema]
                for edge in graph.edges
            ],
        }

        with json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

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
        Concatenate filesystem and AST CSV files into one file.
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

    # =====================================================
    # LOAD
    # =====================================================

    def load(self, nodes_path: Path, edges_path: Optional[Path] = None, *, target: str = "ast"):

        if target not in ("ast", "filesystem"):
            raise ValueError("target must be 'ast' or 'filesystem'")

        graph = getattr(self, target)
        graph.__init__()

        if nodes_path.suffix == ".json":
            self._load_json(nodes_path, graph)
        else:
            self._load_nodes_csv(nodes_path, graph)
            if edges_path:
                self._load_edges_csv(edges_path, graph)

        self._build_indexes()
        return self

    def _load_nodes_csv(self, path: Path, graph: _Graph):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)

            # Skip comment lines
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                header = row
                break

            graph.node_schema = [(name, "") for name in header]

            for row in reader:
                if not row:
                    continue
                node = dict(zip(header, row))
                graph.nodes[node["id"]] = node

    def _load_edges_csv(self, path: Path, graph: _Graph):
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                header = row
                break

            graph.edge_schema = [(name, "") for name in header]

            for row in reader:
                if not row:
                    continue
                edge = dict(zip(header, row))
                graph.edges.append(edge)
                graph.edge_ids.add(edge["id"])

    def _load_json(self, path: Path, graph: _Graph):
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        graph.node_schema = [
            (x["name"], x.get("description", ""))
            for x in data["node_schema"]
        ]

        graph.edge_schema = [
            (x["name"], x.get("description", ""))
            for x in data["edge_schema"]
        ]

        for row in data["nodes"]:
            node = dict(zip([n for n, _ in graph.node_schema], row))
            graph.nodes[node["id"]] = node

        for row in data["edges"]:
            edge = dict(zip([n for n, _ in graph.edge_schema], row))
            graph.edges.append(edge)
            graph.edge_ids.add(edge["id"])

    # =====================================================
    # INDEXING
    # =====================================================

    def _build_indexes(self):

        for graph in (self.filesystem, self.ast):
            graph.out_edges.clear()
            graph.in_edges.clear()

            for edge in graph.edges:
                graph.out_edges[edge["source"]].append(edge)
                graph.in_edges[edge["target"]].append(edge)

        # AST semantic indexing
        self.ast.by_qname.clear()
        self.ast.by_name.clear()
        self.ast.symbols_by_file.clear()

        for nid, node in self.ast.nodes.items():
            qname = node.get("qualified_name")
            name = node.get("name")
            module_path = node.get("module_path")
            lineno = node.get("lineno")
            end_lineno = node.get("end_lineno")

            if qname:
                self.ast.by_qname[qname] = nid

            if name:
                self.ast.by_name[name].append(nid)

            if module_path and lineno and end_lineno:
                try:
                    start = int(lineno)
                    end = int(end_lineno)
                    self.ast.symbols_by_file[module_path].append((start, end, nid))
                except Exception:
                    pass

        for file in self.ast.symbols_by_file:
            self.ast.symbols_by_file[file].sort(key=lambda x: x[0])

    def _remove_nodes_by_predicate(self, graph: _Graph, predicate):
        to_delete = [nid for nid, node in graph.nodes.items() if predicate(node)]

        if not to_delete:
            return

        # Remove nodes
        for nid in to_delete:
            graph.nodes.pop(nid, None)

        # Remove edges touching deleted nodes
        graph.edges = [
            e for e in graph.edges
            if e["source"] not in to_delete and e["target"] not in to_delete
        ]

        graph.edge_ids = {
            e["id"] for e in graph.edges
        }

    def remove_paths(self, paths: List[Path]):

        paths = [Path(p).resolve() for p in paths]

        # Filesystem graph
        def fs_match(node):
            abs_path = node.get("abs_path")
            if not abs_path:
                return False

            try:
                node_path = Path(abs_path).resolve()
            except Exception:
                return False

            for p in paths:
                try:
                    # Exact file match OR inside deleted directory
                    if node_path == p or p in node_path.parents:
                        return True
                except Exception:
                    continue

            return False

        self._remove_nodes_by_predicate(self.filesystem, fs_match)

        # AST graph
        def ast_match(node):
            module_path = node.get("module_path")
            if not module_path:
                return False
            return any(module_path.endswith(str(p.name)) for p in paths)

        self._remove_nodes_by_predicate(self.ast, ast_match)

        self._build_indexes()

    def update_filesystem_paths(
            self,
            paths: List[Path],
            ignore_file=None,
    ):

        paths = [Path(p).resolve() for p in paths]

        # Remove old versions first
        def match(node):
            abs_path = node.get("abs_path")
            if not abs_path:
                return False
            return any(str(abs_path).startswith(str(p)) for p in paths)

        self._remove_nodes_by_predicate(self.filesystem, match)

        # Re-scan only changed paths
        scanner = Scanner(paths, ignore_file=ignore_file)

        scanner.scan_into(self.filesystem)

        self._build_indexes()

    def update_ast_paths(
            self,
            paths: List[Path],
            ignore_file=None,
    ):

        py_paths = [Path(p).resolve() for p in paths if Path(p).suffix == ".py"]

        if not py_paths:
            return

        # Remove old AST nodes for these modules
        def match(node):
            module_path = node.get("module_path")
            if not module_path:
                return False
            return any(module_path.endswith(p.name) for p in py_paths)

        self._remove_nodes_by_predicate(self.ast, match)

        # Re-scan only changed Python files
        scanner = AstScanner(py_paths, ignore_file=ignore_file)

        scanner.scan_into(self.ast)

        self._build_indexes()
