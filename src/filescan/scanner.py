from pathlib import Path
from typing import Optional

from .base import ScannerBase
from .utils import load_ignore_spec


class Scanner(ScannerBase):
    NODE_SCHEMA = [
        ("id", "Unique node ID"),
        ("type", "Node type: 'd' = directory, 'f' = file"),
        ("name", "Base name of the file or directory"),
        ("abs_path", "Absolute path of file or directory"),
        ("size", "File size in bytes; null for directories"),
    ]

    EDGE_SCHEMA = [
        ("id", "Unique edge ID"),
        ("source", "Source node ID"),
        ("target", "Target node ID"),
        ("relation", "Edge relation type"),
    ]

    # -------------------------------------------------
    # Public
    # -------------------------------------------------

    def scan_into(self, graph) -> None:
        """
        Scan filesystem and write into provided graph.
        """

        if self._ignore_spec is None and self.ignore_file is not None:
            self._ignore_spec = load_ignore_spec(self.ignore_file)

        for root in self.root:
            self._walk(graph, root, root=root, parent_id=None)

    # -------------------------------------------------
    # Canonical Identity
    # -------------------------------------------------

    def _canonical_key(self, path: Path, root: Path) -> str:
        """
        Logical identity of node.
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
        graph,
        path: Path,
        root: Path,
        parent_id: Optional[str],
    ) -> None:

        # Ignore (except root)
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

        abs_path = str(path.resolve().as_posix())

        # ---- Add node ----
        node_payload = {
            "type": "d" if is_dir else "f",
            "name": path.name,
            "abs_path": abs_path,
            "size": size,
        }

        node_id = self.add_node(
            graph,
            canonical_key,
            node_payload,
        )

        # ---- Add containment edge ----
        if parent_id is not None:
            edge_key = f"{parent_id}|contains|{node_id}"

            edge_payload = {
                "source": parent_id,
                "target": node_id,
                "relation": "contains",
            }

            self.add_edge(graph, edge_key, edge_payload)

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
                graph,
                child,
                root=root,
                parent_id=node_id,
            )