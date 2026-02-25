from pathlib import Path
from typing import List, Optional
import hashlib

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
    # Identity
    # -------------------------------------------------

    def _node_id(self, path: Path, root: Path) -> str:
        """
        Stable ID = SHA1(root_name + "/" + relative_path)
        """
        root = root.resolve()
        path = path.resolve()

        root_name = root.name or "root"

        if path == root:
            key = root_name
        else:
            rel = path.relative_to(root)
            rel_str = str(rel).replace("\\", "/")
            key = f"{root_name}/{rel_str}"

        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    def _edge_id(self, source: str, target: str, relation: str) -> str:
        key = f"{source}|{relation}|{target}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

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

        node_id = self._node_id(path, root)
        is_dir = path.is_dir()

        size: Optional[int] = None
        if not is_dir:
            try:
                size = path.stat().st_size
            except OSError:
                pass

        # Add node
        self._add_node([
            node_id,
            "d" if is_dir else "f",
            path.name,
            size,
        ])

        # Add edge (parent -> child)
        if parent_id is not None:
            eid = self._edge_id(parent_id, node_id, "contains")
            self._add_edge(eid, parent_id, node_id, "contains")

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