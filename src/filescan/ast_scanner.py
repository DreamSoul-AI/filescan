import astroid
import os
from pathlib import Path
from typing import List, Optional, Union, Dict

from .base import ScannerBase
from .utils import load_ignore_spec


class AstScanner(ScannerBase):
    """
    Astroid-powered semantic scanner.
    Produces cross-file semantic property graph.

    Identity model:
    - Node canonical key = qualified_name
    - Edge canonical key = source|relation|target|lineno
    - ID generation handled safely by ScannerBase
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

        # qualified_name -> node_id
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
    # Module name resolution
    # =====================================================

    def _compute_module_name(self, path: Path, root: Path) -> str:
        rel = path.relative_to(root)
        rel_no_suffix = rel.with_suffix("")
        parts = list(rel_no_suffix.parts)

        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

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

        # Add module node (canonical key = module_name)
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
        doc1 = ""
        if doc:
            doc1 = doc.strip().splitlines()[0]

        # Canonical key = qualified_name
        sid = self._add_node([
            qualified_name,
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
            self._add_edge(
                parent_id,
                sid,
                "contains",
            )

        return sid

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

        module_id = self._qualified_name_to_id.get(module_name)

        # IMPORTS
        for _local, full in import_map.items():
            self._maybe_link(module_id, full, "imports")

        # CALLS
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

        # INHERITANCE
        for node in module.nodes_of_class(astroid.ClassDef):
            child_id = self._qualified_name_to_id.get(node.qname())
            if not child_id:
                continue

            for base in node.bases:
                try:
                    for inferred in base.infer():
                        if hasattr(inferred, "qname"):
                            self._maybe_link(
                                child_id,
                                inferred.qname(),
                                "inherits",
                                lineno=node.lineno,
                                end_lineno=node.lineno,
                            )
                except Exception:
                    continue

        # REFERENCES
        for node in module.nodes_of_class(astroid.Name):
            caller_id = self._resolve_caller_id(node)
            if caller_id is None:
                continue

            symbol = node.name

            if symbol in import_map:
                self._maybe_link(
                    caller_id,
                    import_map[symbol],
                    "references",
                    lineno=node.lineno,
                    end_lineno=node.lineno,
                )
                continue

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
