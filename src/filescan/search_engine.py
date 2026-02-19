import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any

from .graph_loader import GraphLoader


class SearchEngine:
    """
    Hybrid search engine:
    - ripgrep for fast text search
    - GraphLoader for semantic enrichment
    """

    def __init__(self, root: Path, graph: GraphLoader):
        self.root = os.path.abspath(os.fspath(root))
        self.graph = graph

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def search(self, query: str) -> List[Dict[str, Any]]:
        matches = list(self._grep(query))

        if not matches:
            return []

        results = []

        for m in matches:
            file_path = os.path.abspath(m["file"])

            module_path = os.path.normpath(
                os.path.relpath(file_path, self.root)
            )

            symbol_id = None
            if module_path and self.graph.is_semantic_graph():
                symbol_id = self.graph.find_symbol_at(
                    module_path,
                    m["line"],
                )

            results.append({
                "file": str(file_path),
                "line": m["line"],
                "text": m["text"].strip(),
                "symbol_id": symbol_id,
                "symbol": self.graph.nodes.get(symbol_id),
            })
        # TODO: enrich context with associate with definition like node, or just reference.
        return results

    # -------------------------------------------------
    # Ripgrep Layer
    # -------------------------------------------------

    def _grep(self, query: str):
        cmd = [
            "rg",
            "--json",
            "--line-number",
            "--with-filename",
            query,
            self.root,
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        for line in proc.stdout:
            event = json.loads(line)

            if event["type"] == "match":
                yield {
                    "file": event["data"]["path"]["text"],
                    "line": event["data"]["line_number"],
                    "text": event["data"]["lines"]["text"],
                }

