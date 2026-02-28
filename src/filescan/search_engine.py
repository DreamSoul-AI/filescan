import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any

from .graph_builder import GraphBuilder

# -------------------------------------------------
# Sort by semantic priority
# -------------------------------------------------
PRIORITY = {
    "definition": 0,
    "inherits": 1,
    "calls": 2,
    "references": 3,
    "imports": 4,
    "unknown": 5,
}


class SearchEngine:
    """
    Hybrid search engine:
    - ripgrep for fast text search
    - GraphLoader for semantic enrichment
    """

    def __init__(self, root: Path, graph: GraphBuilder):
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

        # Resolve semantic targets by symbol name
        target_ids = set(self.graph.by_name.get(query, []))

        for m in matches:
            file_path = os.path.abspath(m["file"])
            module_path = os.path.normpath(
                os.path.relpath(file_path, self.root)
            )

            match_type = "unknown"
            container_id = None
            container = None

            if module_path and self.graph.is_semantic_graph():
                container_id = self.graph.find_symbol_at(
                    module_path,
                    m["line"],
                )
                container = self.graph.nodes.get(container_id)

            # -------------------------------------------------
            # 1️⃣ Definition
            # -------------------------------------------------
            if container and container.get("lineno"):
                try:
                    if int(container["lineno"]) == m["line"]:
                        match_type = "definition"
                except ValueError:
                    pass

            # -------------------------------------------------
            # 2️⃣ Semantic relation
            # -------------------------------------------------
            if match_type == "unknown" and container_id and target_ids:
                for edge in self.graph.out_edges.get(container_id, []):
                    if edge["target"] in target_ids:
                        match_type = edge["relation"]
                        break

            results.append({
                "file": file_path,
                "line": m["line"],
                "text": m["text"].strip(),
                "symbol_id": container_id,
                "symbol": container,
                "match_type": match_type,
            })

        results.sort(
            key=lambda r: (
                PRIORITY.get(r["match_type"], 99),
                r["file"],
                r["line"],
            )
        )

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
