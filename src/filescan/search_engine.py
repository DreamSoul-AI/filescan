import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


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
    - AST graph for semantic enrichment
    """

    def __init__(self, root: Path, ast_graph):
        """
        ast_graph must be builder.ast
        """
        self.root = Path(root).resolve()
        self.graph = ast_graph

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
            file_path = Path(m["file"]).resolve()

            try:
                module_path = os.path.normpath(
                    os.path.relpath(file_path, self.root)
                )
            except ValueError:
                continue

            container_id = self._find_symbol_at(
                module_path,
                m["line"],
            )

            container = (
                self.graph.nodes.get(container_id)
                if container_id
                else None
            )

            match_type = "unknown"

            # -------------------------------------------------
            # 1️⃣ Definition
            # -------------------------------------------------
            if container and container.get("lineno"):
                try:
                    if int(container["lineno"]) == m["line"]:
                        match_type = "definition"
                except (ValueError, TypeError):
                    pass

            # -------------------------------------------------
            # 2️⃣ Semantic relation
            # -------------------------------------------------
            if match_type == "unknown" and container_id and target_ids:
                for edge in self.graph.out_edges.get(container_id, []):
                    if edge["target"] in target_ids:
                        match_type = edge.get("relation", "unknown")
                        break

            results.append({
                "file": str(file_path),
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
    # Symbol Resolver
    # -------------------------------------------------

    def _find_symbol_at(self, module_path: str, line: int) -> Optional[str]:

        candidates = []

        for start, end, nid in self.graph.symbols_by_file.get(module_path, []):
            if start <= line <= end:
                candidates.append((end - start, nid))

        if not candidates:
            return None

        return min(candidates)[1]

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

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ripgrep (rg) not found. Please install it."
            )

        for line in proc.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "match":
                yield {
                    "file": event["data"]["path"]["text"],
                    "line": event["data"]["line_number"],
                    "text": event["data"]["lines"]["text"],
                }

        proc.wait()