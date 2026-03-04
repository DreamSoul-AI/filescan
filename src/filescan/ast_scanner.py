import astroid
from astroid import nodes

import os
from pathlib import Path
from typing import Optional, Union, Dict

from .base import ScannerBase
from .utils import load_ignore_spec


class AstScanner(ScannerBase):
    """
    Astroid-powered semantic scanner.
    Writes into provided graph (no internal storage).
    """

    NODE_SCHEMA = [
        ("id", "Unique node ID"),
        ("kind", "module | class | function | method"),
        ("name", "Symbol name"),
        ("qualified_name", "Fully qualified symbol name"),
        ("module_path", "Module file path relative to scan root"),
        ("lineno", "Starting line number"),
        ("end_lineno", "Ending line number"),
        ("signature", "Function signature"),
        ("doc", "First line of docstring"),
    ]

    EDGE_SCHEMA = [
        ("id", "Unique edge ID"),
        ("source", "Source node ID"),
        ("target", "Target node ID"),
        ("relation", "contains | imports | calls | creates | inherits | references"),
        ("lineno", "Line number where relation occurs"),
        ("end_lineno", "End line number where relation occurs"),
    ]

    def __init__(
        self,
        root: Union[str, Path],
        ignore_file: Optional[Union[str, Path]] = None,
    ):
        super().__init__(root, ignore_file)

        self._qualified_name_to_id: Dict[str, str] = {}
        self._ast_modules: Dict[str, nodes.Module] = {}
        self._module_imports: Dict[str, Dict[str, str]] = {}

    # =====================================================
    # Public API
    # =====================================================

    def scan_into(self, graph) -> None:
        self._qualified_name_to_id.clear()
        self._ast_modules.clear()
        self._module_imports.clear()

        if self._ignore_spec is None and self.ignore_file:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        # PASS 1 — Definitions
        for root in self.root:
            for path in sorted(root.rglob("*.py")):
                if self._is_ignored(path):
                    continue
                self._collect_definitions(graph, path, root)

        # PASS 2 — Relationships
        for module_name, module in self._ast_modules.items():
            self._resolve_references(graph, module_name, module)

    # =====================================================
    # Helpers
    # =====================================================

    def _get_docstring_first_line(self, node) -> Optional[str]:
        doc_node = getattr(node, "doc_node", None)
        if doc_node is None:
            return None

        value = getattr(doc_node, "value", None)
        if not isinstance(value, str):
            return None

        return value.strip().splitlines()[0]

    def _compute_module_name(self, path: Path, root: Path) -> str:
        rel = path.relative_to(root)
        rel_no_suffix = rel.with_suffix("")
        parts = list(rel_no_suffix.parts)

        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

        return ".".join([root.name] + parts)

    # =====================================================
    # PASS 1 — Definitions
    # =====================================================

    def _collect_definitions(self, graph, path: Path, root: Path) -> None:

        module_path = os.path.normpath(
            os.path.relpath(os.fspath(path), os.fspath(root))
        )

        module_name = self._compute_module_name(path, root)

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return

        try:
            module = astroid.parse(
                text,
                module_name=module_name,
                path=os.fspath(path),
            )
        except Exception:
            return

        self._ast_modules[module_name] = module

        import_map: Dict[str, str] = {}

        for node in module.nodes_of_class(nodes.ImportFrom):
            for name, alias in node.names:
                local = alias or name
                full = f"{node.modname}.{name}"
                import_map[local] = full

        for node in module.nodes_of_class(nodes.Import):
            for name, alias in node.names:
                local = alias or name.split(".")[-1]
                import_map[local] = name

        self._module_imports[module_name] = import_map

        # ---- Add module node ----
        module_id = self._add_symbol(
            graph,
            parent_id=None,
            kind="module",
            name=module_name,
            qualified_name=module_name,
            module_path=module_path,
            lineno=1,
            end_lineno=1,
            signature="",
            doc=self._get_docstring_first_line(module),
        )

        for node in module.body:
            self._visit_definition(graph, node, module_id, module_path)

    def _visit_definition(self, graph, node, parent_id: str, module_path: str) -> None:

        if isinstance(node, nodes.ClassDef):

            cid = self._add_symbol(
                graph,
                parent_id=parent_id,
                kind="class",
                name=node.name,
                qualified_name=node.qname(),
                module_path=module_path,
                lineno=node.lineno,
                end_lineno=node.end_lineno,
                signature="",
                doc=self._get_docstring_first_line(node),
            )

            for child in node.body:
                self._visit_definition(graph, child, cid, module_path)

        elif isinstance(node, nodes.FunctionDef):

            kind = (
                "method"
                if isinstance(node.parent, nodes.ClassDef)
                else "function"
            )

            self._add_symbol(
                graph,
                parent_id=parent_id,
                kind=kind,
                name=node.name,
                qualified_name=node.qname(),
                module_path=module_path,
                lineno=node.lineno,
                end_lineno=node.end_lineno,
                signature=node.args.as_string(),
                doc=self._get_docstring_first_line(node),
            )

    # =====================================================
    # Symbol creation
    # =====================================================

    def _add_symbol(
        self,
        graph,
        parent_id: Optional[str],
        kind: str,
        name: str,
        qualified_name: str,
        module_path: str,
        lineno: int,
        end_lineno: int,
        signature: str,
        doc: Optional[str],
    ) -> str:

        payload = {
            "kind": kind,
            "name": name,
            "qualified_name": qualified_name,
            "module_path": module_path,
            "lineno": lineno,
            "end_lineno": end_lineno,
            "signature": signature,
            "doc": doc or "",
        }

        node_id = self.add_node(
            graph,
            canonical_key=qualified_name,
            payload=payload,
        )

        self._qualified_name_to_id[qualified_name] = node_id

        if parent_id is not None:
            edge_key = f"{parent_id}|contains|{node_id}"
            self.add_edge(
                graph,
                canonical_key=edge_key,
                payload={
                    "source": parent_id,
                    "target": node_id,
                    "relation": "contains",
                    "lineno": None,
                    "end_lineno": None,
                },
            )

        return node_id

    # =====================================================
    # PASS 2 — Relationships
    # =====================================================

    def _resolve_caller_id(self, node) -> Optional[str]:
        scope = node.scope()

        if isinstance(scope, nodes.FunctionDef):
            qname = scope.qname()
        elif isinstance(scope, nodes.ClassDef):
            qname = scope.qname()
        elif isinstance(scope, nodes.Module):
            qname = scope.name
        else:
            return None

        return self._qualified_name_to_id.get(qname)

    def _resolve_references(self, graph, module_name: str, module: nodes.Module) -> None:

        import_map = self._module_imports.get(module_name, {})
        module_id = self._qualified_name_to_id.get(module_name)

        # IMPORTS
        for _local, full in import_map.items():
            self._maybe_link(graph, module_id, full, "imports", None, None)

        # CALLS / CONSTRUCTORS
        for node in module.nodes_of_class(nodes.Call):

            caller_id = self._resolve_caller_id(node)
            if caller_id is None:
                continue

            try:
                for inferred in node.func.infer():

                    if not hasattr(inferred, "qname"):
                        continue

                    relation = "calls"

                    # detect constructor call (class instantiation)
                    if isinstance(inferred, nodes.ClassDef):
                        relation = "creates"

                    self._maybe_link(
                        graph,
                        caller_id,
                        inferred.qname(),
                        relation,
                        node.lineno,
                        getattr(node, "end_lineno", node.lineno),
                    )

            except Exception:
                continue

        # INHERITS
        for node in module.nodes_of_class(nodes.ClassDef):
            child_id = self._qualified_name_to_id.get(node.qname())
            if not child_id:
                continue

            for base in node.bases:
                try:
                    for inferred in base.infer():
                        if hasattr(inferred, "qname"):
                            self._maybe_link(
                                graph,
                                child_id,
                                inferred.qname(),
                                "inherits",
                                node.lineno,
                                node.lineno,
                            )
                except Exception:
                    continue

        # REFERENCES
        for node in module.nodes_of_class(nodes.Name):
            caller_id = self._resolve_caller_id(node)
            if caller_id is None:
                continue

            symbol = node.name

            if symbol in import_map:
                self._maybe_link(
                    graph,
                    caller_id,
                    import_map[symbol],
                    "references",
                    node.lineno,
                    node.lineno,
                )
                continue

            local_candidate = f"{module_name}.{symbol}"
            target_id = self._qualified_name_to_id.get(local_candidate)

            if target_id:
                edge_key = f"{caller_id}|references|{target_id}|{node.lineno}"
                self.add_edge(
                    graph,
                    canonical_key=edge_key,
                    payload={
                        "source": caller_id,
                        "target": target_id,
                        "relation": "references",
                        "lineno": node.lineno,
                        "end_lineno": node.lineno,
                    },
                )

        # TYPE ANNOTATIONS
        for node in module.nodes_of_class(nodes.AnnAssign):

            caller_id = self._resolve_caller_id(node)
            if caller_id is None:
                continue

            ann = node.annotation

            try:
                for inferred in ann.infer():
                    if hasattr(inferred, "qname"):
                        self._maybe_link(
                            graph,
                            caller_id,
                            inferred.qname(),
                            "references",
                            node.lineno,
                            node.lineno,
                        )
            except Exception:
                continue

    # =====================================================
    # Edge helper
    # =====================================================

    def _maybe_link(
        self,
        graph,
        source_id: Optional[str],
        qualified_name: str,
        relation: str,
        lineno: Optional[int],
        end_lineno: Optional[int],
    ) -> None:

        target_id = self._qualified_name_to_id.get(qualified_name)

        if source_id is None or target_id is None:
            return

        edge_key = f"{source_id}|{relation}|{target_id}|{lineno or ''}"

        self.add_edge(
            graph,
            canonical_key=edge_key,
            payload={
                "source": source_id,
                "target": target_id,
                "relation": relation,
                "lineno": lineno,
                "end_lineno": end_lineno,
            },
        )