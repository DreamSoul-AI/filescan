import astroid
import os
import hashlib
from pathlib import Path
from typing import List, Optional, Union, Dict

from .base import ScannerBase
from .utils import load_ignore_spec


class AstScanner(ScannerBase):
    """
    Astroid-powered semantic scanner.
    Produces cross-file semantic property graph.

    Node IDs: SHA1(qualified_name)[:16]
    Edge IDs: SHA1(source|relation|target|lineno)[:16]
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
        ("relation", "contains | imports | calls | inherits | references"),
        ("lineno", "Line number where relation occurs"),
        ("end_lineno", "End line number where relation occurs"),
    ]

    def __init__(
        self,
        root: Union[str, Path],
        ignore_file: Optional[Union[str, Path]] = None,
        output: Optional[Union[str, Path]] = None,
    ):
        super().__init__(root, ignore_file, output)

        # qualified_name -> node_id (hashed)
        self._qualified_name_to_id: Dict[str, str] = {}

        # module_name -> astroid.Module
        self._ast_modules: Dict[str, astroid.Module] = {}

        # module_name -> {local_name: full_qualified_name}
        self._module_imports: Dict[str, Dict[str, str]] = {}

    # =====================================================
    # Public API
    # =====================================================

    def scan(self) -> List[list]:
        self.reset()
        self._qualified_name_to_id.clear()
        self._ast_modules.clear()
        self._module_imports.clear()

        if self._ignore_spec is None and self.ignore_file:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        # PASS 1 — Collect definitions + imports
        for root in self.root:
            for path in sorted(root.rglob("*.py")):
                if self._is_ignored(path):
                    continue
                self._collect_definitions(path, root)

        # PASS 2 — Resolve semantic relationships
        for module_name, module in self._ast_modules.items():
            self._resolve_references(module_name, module)

        return self._nodes

    # =====================================================
    # Identity helpers
    # =====================================================

    @staticmethod
    def _sha16(s: str) -> str:
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]

    def _node_id(self, qualified_name: str) -> str:
        return self._sha16(qualified_name)

    def _edge_id(self, source: str, target: str, relation: str, lineno: Optional[int]) -> str:
        key = f"{source}|{relation}|{target}|{lineno or ''}"
        return self._sha16(key)

    # =====================================================
    # Module name resolution
    # =====================================================

    def _compute_module_name(self, path: Path, root: Path) -> str:
        rel = path.relative_to(root)
        rel_no_suffix = rel.with_suffix("")
        parts = list(rel_no_suffix.parts)

        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

        # Namespace with root folder name
        return ".".join([root.name] + parts)

    # =====================================================
    # PASS 1 — Definitions + Import Map
    # =====================================================

    def _collect_definitions(self, path: Path, root: Path) -> None:
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

        for node in module.nodes_of_class(astroid.ImportFrom):
            for name, alias in node.names:
                local_name = alias or name
                full_name = f"{node.modname}.{name}"
                import_map[local_name] = full_name

        for node in module.nodes_of_class(astroid.Import):
            for name, alias in node.names:
                local_name = alias or name.split(".")[-1]
                import_map[local_name] = name

        self._module_imports[module_name] = import_map

        # Add module node
        mid = self._add_symbol(
            parent_id=None,
            kind="module",
            name=module_name,
            qualified_name=module_name,
            module_path=module_path,
            lineno=1,
            end_lineno=1,
            signature="",
            doc=module.doc,
        )

        for node in module.body:
            self._visit_definition(node, mid, module_path)

    def _visit_definition(self, node, parent_id: str, module_path: str) -> None:
        if isinstance(node, astroid.ClassDef):
            cid = self._add_symbol(
                parent_id=parent_id,
                kind="class",
                name=node.name,
                qualified_name=node.qname(),
                module_path=module_path,
                lineno=node.lineno,
                end_lineno=node.end_lineno,
                signature="",
                doc=node.doc,
            )

            for child in node.body:
                self._visit_definition(child, cid, module_path)

        elif isinstance(node, astroid.FunctionDef):
            kind = "method" if isinstance(node.parent, astroid.ClassDef) else "function"

            self._add_symbol(
                parent_id=parent_id,
                kind=kind,
                name=node.name,
                qualified_name=node.qname(),
                module_path=module_path,
                lineno=node.lineno,
                end_lineno=node.end_lineno,
                signature=node.args.as_string(),
                doc=node.doc,
            )

    # =====================================================
    # Symbol Creation
    # =====================================================

    def _add_symbol(
        self,
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
        sid = self._node_id(qualified_name)

        doc1 = ""
        if doc:
            doc1 = doc.strip().splitlines()[0]

        self._add_node([
            sid,
            kind,
            name,
            qualified_name,
            module_path,
            lineno,
            end_lineno,
            signature,
            doc1,
        ])

        self._qualified_name_to_id[qualified_name] = sid

        if parent_id is not None:
            self._add_edge(parent_id, sid, "contains")

        return sid

    # =====================================================
    # Edge Creation (scanner-level identity)
    # =====================================================

    def _add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        lineno: Optional[int] = None,
        end_lineno: Optional[int] = None,
    ) -> str:
        edge_id = self._edge_id(source, target, relation, lineno)

        self._edges.append([
            edge_id,
            source,
            target,
            relation,
            lineno,
            end_lineno,
        ])

        return edge_id

    # =====================================================
    # PASS 2 — Semantic Resolution
    # =====================================================

    def _resolve_caller_id(self, node) -> Optional[str]:
        scope = node.scope()

        if isinstance(scope, astroid.FunctionDef):
            qname = scope.qname()
        elif isinstance(scope, astroid.ClassDef):
            qname = scope.qname()
        elif isinstance(scope, astroid.Module):
            qname = scope.name
        else:
            return None

        return self._qualified_name_to_id.get(qname)

    def _resolve_references(self, module_name: str, module: astroid.Module) -> None:
        import_map = self._module_imports.get(module_name, {})

        # -------------------------
        # IMPORTS (structural)
        # -------------------------
        module_id = self._qualified_name_to_id.get(module_name)
        for _local, full in import_map.items():
            self._maybe_link(module_id, full, "imports")

        # -------------------------
        # CALLS (function-level)
        # -------------------------
        for node in module.nodes_of_class(astroid.Call):
            caller_id = self._resolve_caller_id(node)
            if caller_id is None:
                continue

            try:
                for inferred in node.func.infer():
                    if hasattr(inferred, "qname"):
                        self._maybe_link(
                            caller_id,
                            inferred.qname(),
                            "calls",
                            lineno=node.lineno,
                            end_lineno=getattr(node, "end_lineno", node.lineno),
                        )
            except Exception:
                continue

        # -------------------------
        # INHERITANCE (structural)
        # -------------------------
        for node in module.nodes_of_class(astroid.ClassDef):
            child_id = self._qualified_name_to_id.get(node.qname())
            if not child_id:
                continue

            for base in node.bases:
                base_name = None
                if isinstance(base, astroid.Name):
                    base_name = base.name
                elif isinstance(base, astroid.Attribute):
                    base_name = base.attrname

                if not base_name:
                    continue

                # Imported base
                if base_name in import_map:
                    self._maybe_link(
                        child_id,
                        import_map[base_name],
                        "inherits",
                        lineno=node.lineno,
                        end_lineno=node.lineno,
                    )
                    continue

                # Same-module base
                local_candidate = f"{module_name}.{base_name}"
                if local_candidate in self._qualified_name_to_id:
                    self._add_edge(
                        child_id,
                        self._qualified_name_to_id[local_candidate],
                        "inherits",
                        lineno=node.lineno,
                        end_lineno=node.lineno,
                    )

        # -------------------------
        # REFERENCES (function-level)
        # -------------------------
        for node in module.nodes_of_class(astroid.Name):
            caller_id = self._resolve_caller_id(node)
            if caller_id is None:
                continue

            symbol = node.name

            # Imported reference
            if symbol in import_map:
                self._maybe_link(
                    caller_id,
                    import_map[symbol],
                    "references",
                    lineno=node.lineno,
                    end_lineno=node.lineno,
                )
                continue

            # Same-module reference
            local_candidate = f"{module_name}.{symbol}"
            if local_candidate in self._qualified_name_to_id:
                self._add_edge(
                    caller_id,
                    self._qualified_name_to_id[local_candidate],
                    "references",
                    lineno=node.lineno,
                    end_lineno=node.lineno,
                )

    # =====================================================
    # Edge helper
    # =====================================================

    def _maybe_link(
        self,
        source_id: Optional[str],
        qualified_name: str,
        relation: str,
        lineno: Optional[int] = None,
        end_lineno: Optional[int] = None,
    ) -> None:
        target_id = self._qualified_name_to_id.get(qualified_name)
        if source_id is not None and target_id is not None:
            self._add_edge(
                source_id,
                target_id,
                relation,
                lineno,
                end_lineno,
            )