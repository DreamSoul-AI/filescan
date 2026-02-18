# filescan/search_engine.py

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
        self.root = root.resolve()
        self.graph = graph

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def search(self, query: str) -> List[Dict[str, Any]]:
        matches = list(self._grep(query))

        if not matches:
            return []

        enriched = []

        for m in matches:
            file_path = Path(m["file"]).resolve()

            try:
                rel_path = file_path.relative_to(self.root)
                module_path = str(rel_path).replace("\\", "/")
            except ValueError:
                module_path = None

            symbol_id = None
            if module_path and self.graph.is_semantic_graph():
                symbol_id = self.graph.find_symbol_at(
                    module_path,
                    m["line"],
                )

            enriched.append({
                "file": str(file_path),
                "line": m["line"],
                "text": m["text"].strip(),
                "symbol_id": symbol_id,
                "symbol": self.graph.nodes.get(symbol_id),
            })

        return self._group_by_symbol(enriched)

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
            str(self.root),
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

    # -------------------------------------------------
    # Group Results
    # -------------------------------------------------

    def _group_by_symbol(self, results: List[Dict]) -> List[Dict]:
        grouped = {}

        for r in results:
            sid = r["symbol_id"]

            if sid not in grouped:
                grouped[sid] = {
                    "symbol": r["symbol"],
                    "matches": [],
                }

            grouped[sid]["matches"].append(r)

        return list(grouped.values())
