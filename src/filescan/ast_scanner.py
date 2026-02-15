import ast
from pathlib import Path
from typing import List, Optional, Union, Dict

from .base import ScannerBase
from .utils import load_ignore_spec


class AstScanner(ScannerBase):
    """
    Python AST scanner that produces a property-graph representation
    of semantic symbols.

    Nodes:
        module | class | function | method

    Edges:
        contains (parent → child)
    """

    NODE_SCHEMA = [
        ("id", "Unique node ID"),
        ("kind", "Symbol kind: module | class | function | method"),
        ("name", "Symbol name"),
        ("qualified_name", "Fully qualified symbol name"),
        ("module_path", "Module file path relative to scan root"),
        ("lineno", "Starting line number (1-based)"),
        ("end_lineno", "Ending line number (inclusive)"),
        ("col_offset", "Starting column offset (0-based)"),
        ("end_col_offset", "Ending column offset (0-based)"),
        ("signature", "Function or method signature (best-effort)"),
        ("doc", "First line of docstring, if any"),
    ]

    def __init__(
        self,
        root: Union[str, Path],
        ignore_file: Optional[Union[str, Path]] = None,
        output: Optional[Union[str, Path]] = None,
    ):
        super().__init__(root, ignore_file=ignore_file, output=output)

        # Internal lookup maps
        self._id_to_kind: Dict[int, str] = {}
        self._id_to_name: Dict[int, str] = {}

    # =====================================================
    # Public API
    # =====================================================

    def scan(self) -> List[list]:
        """
        Scan project root for Python files and extract AST symbols.
        """
        self.reset()
        self._id_to_kind.clear()
        self._id_to_name.clear()

        if self._ignore_spec is None and self.ignore_file is not None:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        for path in sorted(self.root.rglob("*.py")):
            if self._is_ignored(path):
                continue
            self._scan_file(path)

        return self._nodes

    # =====================================================
    # Internal Symbol Construction
    # =====================================================

    def _add_symbol(
        self,
        *,
        parent_id: Optional[int],
        kind: str,
        name: str,
        qualified_name: str,
        module_path: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        signature: str,
        doc: Optional[str],
    ) -> int:
        """
        Add a symbol node and create 'contains' edge if parent exists.
        """
        sid = self._next_node_id_value()

        self._id_to_kind[sid] = kind
        self._id_to_name[sid] = name

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
            col_offset,
            end_col_offset,
            signature,
            doc1,
        ])

        if parent_id is not None:
            self._add_edge(parent_id, sid, "contains")

        return sid

    def _kind_of(self, symbol_id: Optional[int]) -> str:
        if symbol_id is None:
            return ""
        return self._id_to_kind.get(symbol_id, "")

    # =====================================================
    # File Processing
    # =====================================================

    def _scan_file(self, path: Path) -> None:
        module_path = str(path.relative_to(self.root)).replace("\\", "/")

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return

        try:
            tree = ast.parse(text, filename=module_path)
        except SyntaxError:
            return

        visitor = _SymbolVisitor(self, module_path)
        visitor.visit(tree)


# =========================================================
# AST Visitor
# =========================================================

class _SymbolVisitor(ast.NodeVisitor):

    def __init__(self, scanner: AstScanner, module_path: str):
        self.scanner = scanner
        self.module_path = module_path
        self.stack: List[int] = []

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def _current_qualified_name(self, name: str) -> str:
        parts = []
        for sid in self.stack:
            parts.append(self.scanner._id_to_name[sid])
        parts.append(name)
        return ".".join(parts)

    # -----------------------------------------------------
    # Node Visitors
    # -----------------------------------------------------

    def visit_Module(self, node: ast.Module) -> None:
        name = self.module_path.replace("/", ".")
        if name.endswith(".py"):
            name = name[:-3]

        mid = self.scanner._add_symbol(
            parent_id=None,
            kind="module",
            name=name,
            qualified_name=name,
            module_path=self.module_path,
            lineno=1,
            end_lineno=getattr(node, "end_lineno", 1),
            col_offset=0,
            end_col_offset=0,
            signature="",
            doc=ast.get_docstring(node),
        )

        self.stack.append(mid)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        parent_id = self.stack[-1] if self.stack else None
        qname = self._current_qualified_name(node.name)

        cid = self.scanner._add_symbol(
            parent_id=parent_id,
            kind="class",
            name=node.name,
            qualified_name=qname,
            module_path=self.module_path,
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", node.lineno),
            col_offset=node.col_offset,
            end_col_offset=getattr(node, "end_col_offset", node.col_offset),
            signature="",
            doc=ast.get_docstring(node),
        )

        self.stack.append(cid)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node)

    def _handle_function(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
    ) -> None:
        parent_id = self.stack[-1] if self.stack else None
        parent_kind = self.scanner._kind_of(parent_id)

        kind = "method" if parent_kind == "class" else "function"
        sig = _format_signature(node)
        qname = self._current_qualified_name(node.name)

        fid = self.scanner._add_symbol(
            parent_id=parent_id,
            kind=kind,
            name=node.name,
            qualified_name=qname,
            module_path=self.module_path,
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", node.lineno),
            col_offset=node.col_offset,
            end_col_offset=getattr(node, "end_col_offset", node.col_offset),
            signature=sig,
            doc=ast.get_docstring(node),
        )

        self.stack.append(fid)
        self.generic_visit(node)
        self.stack.pop()


# =========================================================
# Signature Formatting
# =========================================================

def _format_signature(
    node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
) -> str:
    """
    Best-effort static signature formatter.
    No evaluation, no imports, no defaults rendering.
    """

    def arg_name(a: ast.arg) -> str:
        return a.arg

    parts: List[str] = []

    posonly = getattr(node.args, "posonlyargs", [])
    for a in posonly:
        parts.append(arg_name(a))
    if posonly:
        parts.append("/")

    for a in node.args.args:
        parts.append(arg_name(a))

    if node.args.vararg:
        parts.append("*" + node.args.vararg.arg)

    if node.args.kwonlyargs:
        if not node.args.vararg:
            parts.append("*")
        for a in node.args.kwonlyargs:
            parts.append(arg_name(a))

    if node.args.kwarg:
        parts.append("**" + node.args.kwarg.arg)

    return "(" + ", ".join(parts) + ")"