import os
import csv
import json
import re
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

    def export_ast_mermaid(
            self,
            output_path: Union[str, Path],
            *,
            show_private: bool = False,
            module_path_filter: Optional[str] = None,
            title: str = "AST UML",
    ) -> Path:
        output_path = Path(output_path)

        nodes: Dict[str, dict] = {}
        for nid, node in self.ast.nodes.items():
            if module_path_filter:
                module_path = node.get("module_path", "")
                if module_path_filter not in Path(module_path).as_posix():
                    continue

            nodes[nid] = {
                "kind": node.get("kind", ""),
                "name": node.get("name", ""),
                "qname": node.get("qualified_name", ""),
                "signature": node.get("signature", ""),
            }

        edges: List[Tuple[str, str, str]] = []
        for edge in self.ast.edges:
            src = edge.get("source")
            tgt = edge.get("target")
            rel = edge.get("relation")
            if not src or not tgt or not rel:
                continue
            if src not in nodes or tgt not in nodes:
                continue
            edges.append((src, tgt, rel))

        uml = self._ast_to_mermaid(nodes, edges, show_private=show_private)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(uml)
            f.write("\n")

        return output_path

    @staticmethod
    def _safe_mermaid_name(name: str) -> str:
        return re.sub(r"[^0-9A-Za-z_]", "_", name)

    @staticmethod
    def _simplify_signature(signature: str) -> str:
        if not signature:
            return ""

        signature = re.sub(r"\[[^\]]*\]", "", signature)
        signature = re.sub(r"->.*", "", signature)

        params: List[str] = []
        for part in signature.split(","):
            part = part.strip()
            if not part:
                continue

            part = re.sub(r":.*", "", part)
            part = re.sub(r"=.*", "", part).strip()
            if (
                    part
                    and part != "self"
                    and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", part)
            ):
                params.append(part)

        return ", ".join(params)

    @staticmethod
    def _find_enclosing_class(
            nid: Optional[str],
            parent: Dict[str, str],
            nodes: Dict[str, dict],
    ) -> Optional[str]:
        while nid:
            if nodes.get(nid, {}).get("kind") == "class":
                return nid
            nid = parent.get(nid)
        return None

    def _ast_to_mermaid(
            self,
            nodes: Dict[str, dict],
            edges: List[Tuple[str, str, str]],
            *,
            show_private: bool = False,
    ) -> str:
        parent: Dict[str, str] = {}
        for src, tgt, rel in edges:
            if rel == "contains":
                parent[tgt] = src

        classes: Dict[str, str] = {}
        methods: Dict[str, List[str]] = {}
        method_sig: Dict[str, str] = {}

        for nid, info in nodes.items():
            if info["kind"] == "class":
                classes[nid] = info["name"]
            elif info["kind"] == "method":
                method_sig[nid] = info.get("signature", "")
                class_id = parent.get(nid)
                if class_id:
                    methods.setdefault(class_id, []).append(nid)

        lines = ["```mermaid", "classDiagram"]
        for class_id, class_name in sorted(classes.items(), key=lambda kv: kv[1]):
            lines.append(f"class {self._safe_mermaid_name(class_name)} {{")
            for method_id in sorted(methods.get(class_id, []), key=lambda x: nodes[x]["name"]):
                method_name = nodes[method_id]["name"]
                if not show_private and method_name.startswith("_"):
                    continue

                sig = self._simplify_signature(method_sig.get(method_id, ""))
                if sig:
                    lines.append(f"    +{method_name}({sig})")
                else:
                    lines.append(f"    +{method_name}()")
            lines.append("}")

        inheritance = set()
        for src, tgt, rel in edges:
            if rel == "inherits" and src in classes and tgt in classes:
                lines.append(f"{self._safe_mermaid_name(classes[tgt])} <|-- {self._safe_mermaid_name(classes[src])}")
                inheritance.add((src, tgt))

        seen = set()
        for src, tgt, rel in edges:
            if rel not in ("calls", "references", "imports", "creates"):
                continue

            class_src = self._find_enclosing_class(src, parent, nodes)
            class_tgt = self._find_enclosing_class(tgt, parent, nodes)
            if not class_src or not class_tgt:
                continue
            if class_src == class_tgt:
                continue
            if class_src not in classes or class_tgt not in classes:
                continue
            if (class_src, class_tgt) in inheritance or (class_tgt, class_src) in inheritance:
                continue

            pair = (class_src, class_tgt)
            if pair not in seen:
                lines.append(f"{self._safe_mermaid_name(classes[class_src])} --> {self._safe_mermaid_name(classes[class_tgt])}")
                seen.add(pair)

        lines.append("```")
        return "\n".join(lines)

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
