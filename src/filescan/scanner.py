from pathlib import Path
from typing import List, Optional

from .base import ScannerBase
from .utils import load_ignore_spec


class Scanner(ScannerBase):
    SCHEMA = [
        ("id", "Unique integer ID for this node"),
        ("parent_id", "ID of parent node, or null for root"),
        ("type", "Node type: 'd' = directory, 'f' = file"),
        ("name", "Base name of the file or directory"),
        ("size", "File size in bytes; null for directories"),
    ]

    # -------- public --------

    def scan(self) -> List[list]:
        """
        Scan the filesystem tree rooted at ``self.root``.

        Returns
        -------
        list of list
            Flat list of nodes following ``SCHEMA`` order.
        """
        self.reset()

        if self._ignore_spec is None and self.ignore_file is not None:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        self._walk(self.root, parent_id=None)
        return self._nodes

    # -------- internal --------

    def _walk(self, path: Path, parent_id: Optional[int]) -> None:
        """
        Recursively walk the directory tree and collect nodes.
        """
        # Do not ignore the root itself
        if parent_id is not None and self._is_ignored(path):
            return

        node_id = self._next_id_value()
        is_dir = path.is_dir()

        size: Optional[int] = None
        if not is_dir:
            try:
                size = path.stat().st_size
            except OSError:
                pass

        self._nodes.append([
            node_id,
            parent_id,
            "d" if is_dir else "f",
            path.name,
            size,
        ])

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
