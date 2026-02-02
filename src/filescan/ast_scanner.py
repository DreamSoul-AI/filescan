import ast
from pathlib import Path
from typing import List, Optional, Union, Dict

from .base import ScannerBase
from .utils import load_ignore_spec


class AstScanner(ScannerBase):
    """
    Python AST scanner that produces a flat, graph-style representation
    of symbols in a Python project.

    Each row represents a semantic symbol:
    - module
    - class
    - function
    - method
    """

    SCHEMA = [
        ("id", "Unique integer ID for this symbol"),
        ("parent_id", "ID of parent symbol, or null for module"),
        ("kind", "Symbol kind: module | class | function | method"),
        ("name", "Symbol name"),
        ("module_path", "Module file path relative to scan root"),
        ("lineno", "Starting line number (1-based)"),
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
        self._id_to_kind: Dict[int, str] = {}

    # -------- public --------

    def scan(self) -> List[list]:
        """
        Scan the project root for Python files and extract AST symbols.
        """
        self.reset()
        self._id_to_kind.clear()

        if self._ignore_spec is None and self.ignore_file is not None:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        for path in sorted(self.root.rglob("*.py")):
            if self._is_ignored(path):
                continue
            self._scan_file(path)

        return self._nodes

    # -------- internal helpers --------

    def _next_symbol_id(self) -> int:
        return self._next_id_value()

    def _add_symbol(
        self,
        *,
        parent_id: Optional[int],
        kind: str,
        name: str,
        module_path: str,
        lineno: int,
        signature: str,
        doc: Optional[str],
    ) -> int:
        sid = self._next_symbol_id()
        self._id_to_kind[sid] = kind

        doc1 = ""
        if doc:
            doc1 = doc.strip().splitlines()[0]

        self._nodes.append([
            sid,
            parent_id,
            kind,
            name,
            module_path,
            lineno,
            signature,
            doc1,
        ])
        return sid

    def _kind_of(self, symbol_id: Optional[int]) -> str:
        if symbol_id is None:
            return ""
        return self._id_to_kind.get(symbol_id, "")

    def _scan_file(self, path: Path) -> None:
        module_path = str(path.relative_to(self.root)).replace("\\", "/")

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Skip non-UTF8 files
            return

        try:
            tree = ast.parse(text, filename=module_path)
        except SyntaxError:
            # Skip broken Python files
            return

        visitor = _SymbolVisitor(self, module_path=module_path)
        visitor.visit(tree)


# ------------------------
# AST visitor
# ------------------------

class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self, scanner: AstScanner, module_path: str):
        self.scanner = scanner
        self.module_path = module_path
        self.stack: List[int] = []

    def visit_Module(self, node: ast.Module) -> None:
        name = self.module_path.replace("/", ".")
        if name.endswith(".py"):
            name = name[:-3]

        mid = self.scanner._add_symbol(
            parent_id=None,
            kind="module",
            name=name,
            module_path=self.module_path,
            lineno=1,
            signature="",
            doc=ast.get_docstring(node),
        )

        self.stack.append(mid)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        parent_id = self.stack[-1] if self.stack else None

        cid = self.scanner._add_symbol(
            parent_id=parent_id,
            kind="class",
            name=node.name,
            module_path=self.module_path,
            lineno=getattr(node, "lineno", 1),
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

        fid = self.scanner._add_symbol(
            parent_id=parent_id,
            kind=kind,
            name=node.name,
            module_path=self.module_path,
            lineno=getattr(node, "lineno", 1),
            signature=sig,
            doc=ast.get_docstring(node),
        )

        self.stack.append(fid)
        self.generic_visit(node)
        self.stack.pop()


# ------------------------
# signature formatting
# ------------------------

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

    # positional-only args (Python 3.8+)
    posonly = getattr(node.args, "posonlyargs", [])
    for a in posonly:
        parts.append(arg_name(a))
    if posonly:
        parts.append("/")

    # positional args
    for a in node.args.args:
        parts.append(arg_name(a))

    # *args
    if node.args.vararg:
        parts.append("*" + node.args.vararg.arg)

    # keyword-only args
    if node.args.kwonlyargs:
        if not node.args.vararg:
            parts.append("*")
        for a in node.args.kwonlyargs:
            parts.append(arg_name(a))

    # **kwargs
    if node.args.kwarg:
        parts.append("**" + node.args.kwarg.arg)

    return "(" + ", ".join(parts) + ")"
