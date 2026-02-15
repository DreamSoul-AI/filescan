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
        """
        Scan the filesystem tree rooted at `self.root`.

        Returns
        -------
        list of list
            Flat list of nodes following NODE_SCHEMA order.
        """
        self.reset()

        if self._ignore_spec is None and self.ignore_file is not None:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        self._walk(self.root, parent_id=None)
        return self._nodes

    # -------------------------------------------------
    # Internal
    # -------------------------------------------------

    def _walk(self, path: Path, parent_id: Optional[int]) -> None:
        """
        Recursively walk the directory tree and collect nodes + edges.
        """

        # Do not ignore the root itself
        if parent_id is not None and self._is_ignored(path):
            return

        node_id = self._next_node_id_value()
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
            self._add_edge(parent_id, node_id, "contains")

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
            self._walk(child, parent_id=node_id)