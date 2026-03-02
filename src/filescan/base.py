import os
import hashlib
from pathlib import Path
from typing import List, Optional, Union, Any
from importlib import resources


class ScannerBase:
    """
    Stateless base class for graph scanners.

    Responsibilities:
    - Deterministic node ID generation (collision-safe)
    - Deterministic edge ID generation (collision-safe)
    - Ignore handling
    - No graph storage
    - No export logic
    - No schema assumptions
    """

    NODE_SCHEMA: List[tuple] = []
    EDGE_SCHEMA: List[tuple] = []

    DEFAULT_IGNORE_PATH = resources.files("filescan").joinpath("default.fscanignore")
    HASH_INDEX = 8

    # =====================================================
    # Initialization
    # =====================================================

    def __init__(
        self,
        root: Union[str, Path, List[Union[str, Path]]],
        ignore_file: Optional[Union[str, Path]] = None,
    ):
        if isinstance(root, (str, Path)):
            roots = [root]
        else:
            roots = root

        self.root: List[Path] = [
            Path(r).expanduser().resolve() for r in roots
        ]

        self.ignore_file = (
            Path(ignore_file).expanduser().resolve()
            if ignore_file is not None
            else Path(self.DEFAULT_IGNORE_PATH)
        )

        self._ignore_spec: Optional[Any] = None

        # Collision guards (ID determinism)
        self._node_key_to_id: dict[str, str] = {}
        self._node_id_to_key: dict[str, str] = {}

        self._edge_key_to_id: dict[str, str] = {}
        self._edge_id_to_key: dict[str, str] = {}

    # =====================================================
    # Hash utility
    # =====================================================

    @staticmethod
    def _hash(s: str, index: int) -> str:
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:index]

    # =====================================================
    # Node ID generation
    # =====================================================

    def generate_node_id(self, canonical_key: str) -> str:
        """
        Deterministic collision-safe node ID.
        """
        existing = self._node_key_to_id.get(canonical_key)
        if existing:
            return existing

        salt = 0

        while True:
            candidate = canonical_key if salt == 0 else f"{canonical_key}#{salt}"
            node_id = self._hash(candidate, self.HASH_INDEX)

            existing_key = self._node_id_to_key.get(node_id)

            if existing_key is None:
                self._node_id_to_key[node_id] = canonical_key
                self._node_key_to_id[canonical_key] = node_id
                return node_id

            if existing_key == canonical_key:
                return node_id

            salt += 1

    # =====================================================
    # Edge ID generation
    # =====================================================

    def generate_edge_id(self, canonical_key: str) -> str:
        """
        Deterministic collision-safe edge ID.
        Canonical key must be constructed by concrete scanner.
        """
        existing = self._edge_key_to_id.get(canonical_key)
        if existing:
            return existing

        salt = 0

        while True:
            candidate = canonical_key if salt == 0 else f"{canonical_key}#{salt}"
            edge_id = self._hash(candidate, self.HASH_INDEX)

            existing_key = self._edge_id_to_key.get(edge_id)

            if existing_key is None:
                self._edge_id_to_key[edge_id] = canonical_key
                self._edge_key_to_id[canonical_key] = edge_id
                return edge_id

            if existing_key == canonical_key:
                return edge_id

            salt += 1

    # =====================================================
    # Graph write helpers (schema-agnostic)
    # =====================================================

    def add_node(self, graph, canonical_key: str, payload: dict) -> str:
        """
        Add node to graph.

        payload must contain all schema fields EXCEPT 'id'.
        """
        node_id = self.generate_node_id(canonical_key)

        if node_id in graph.nodes:
            return node_id

        payload = dict(payload)
        payload["id"] = node_id

        graph.nodes[node_id] = payload
        return node_id

    def add_edge(self, graph, canonical_key: str, payload: dict) -> str:
        """
        Add edge to graph.

        payload must contain all schema fields EXCEPT 'id'.
        """
        edge_id = self.generate_edge_id(canonical_key)

        if edge_id in graph.edge_ids:
            return edge_id

        payload = dict(payload)
        payload["id"] = edge_id

        graph.edge_ids.add(edge_id)
        graph.edges.append(payload)

        return edge_id

    # =====================================================
    # Ignore Handling
    # =====================================================

    def _is_ignored(self, path: Path) -> bool:
        if self._ignore_spec is None:
            return False

        for root in self.root:
            try:
                rel = path.relative_to(root)
                break
            except ValueError:
                continue
        else:
            return False

        rel_str = os.path.normpath(str(rel))

        if path.is_dir():
            rel_str += os.sep

        rel_str = rel_str.replace(os.sep, "/")

        return bool(self._ignore_spec.match_file(rel_str))