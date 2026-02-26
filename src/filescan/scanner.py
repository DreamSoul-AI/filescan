from pathlib import Path
from typing import List, Optional

from .base import ScannerBase
from .utils import load_ignore_spec


class Scanner(ScannerBase):
    NODE_SCHEMA = [
        ("id", "Unique node ID"),
        ("type", "Node type: 'd' = directory, 'f' = file"),
        ("name", "Base name of the file or directory"),
        ("size", "File size in bytes; null for directories"),
    ]

    # -------------------------------------------------
    # Public
    # -------------------------------------------------

    def scan(self) -> List[list]:
        self.reset()

        if self._ignore_spec is None and self.ignore_file is not None:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        for root in self.root:
            self._walk(root, root=root, parent_id=None)

        return self._nodes

    # -------------------------------------------------
    # Canonical Identity
    # -------------------------------------------------

    def _canonical_key(self, path: Path, root: Path) -> str:
        """
        Logical identity of node.
        This is what defines uniqueness.
        Hashing is handled by ScannerBase.
        """
        root = root.resolve()
        path = path.resolve()

        root_name = root.name or "root"

        if path == root:
            return root_name

        rel = path.relative_to(root)
        rel_str = str(rel).replace("\\", "/")

        return f"{root_name}/{rel_str}"

    # -------------------------------------------------
    # Internal Walk
    # -------------------------------------------------

    def _walk(
        self,
        path: Path,
        root: Path,
        parent_id: Optional[str],
    ) -> None:
        """
        Recursively walk directory tree and collect nodes + edges.
        """

        # Do not ignore the root itself
        if parent_id is not None and self._is_ignored(path):
            return

        canonical_key = self._canonical_key(path, root)
        is_dir = path.is_dir()

        size: Optional[int] = None
        if not is_dir:
            try:
                size = path.stat().st_size
            except OSError:
                pass

        # Add node (ID generated safely by base class)
        node_id = self._add_node([
            canonical_key,
            "d" if is_dir else "f",
            path.name,
            size,
        ])

        # Add containment edge
        if parent_id is not None:
            self._add_edge(
                parent_id,
                node_id,
                "contains",
            )

        if not is_dir:
            return

        try:
            children = sorted(
                path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except OSError:
            return

        for child in children:
            self._walk(
                child,
                root=root,
                parent_id=node_id,
            )