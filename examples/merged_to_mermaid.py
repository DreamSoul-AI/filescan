from pathlib import Path
import csv
import re
import argparse
from typing import Dict, Tuple, List

SHOW_PRIVATE = False


def safe_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z_]", "_", name)


def load_merged(path: Path) -> Tuple[Dict[str, dict], List[Tuple[str, str, str]]]:
    section = None
    nodes: Dict[str, dict] = {}
    edges: List[Tuple[str, str, str]] = []

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

            if row[0].startswith("#"):
                if "AST NODES" in row[0]:
                    section = "ast_nodes"
                elif "AST EDGES" in row[0]:
                    section = "ast_edges"
                continue

            if section == "ast_nodes":
                if len(row) < 5:
                    continue

                nid, kind, name, qname, module_path = row[:5]

                p = Path(module_path).as_posix()

                if "src/filescan" not in p:
                    continue

                signature = row[7] if len(row) > 7 else ""

                nodes[nid] = {
                    "kind": kind,
                    "name": name,
                    "qname": qname,
                    "signature": signature,
                }

            elif section == "ast_edges":
                if len(row) < 4:
                    continue

                _, src, tgt, rel = row[:4]
                edges.append((src, tgt, rel))

    edges = [(s, t, r) for s, t, r in edges if s in nodes and t in nodes]

    return nodes, edges


def simplify_signature(sig: str) -> str:
    if not sig:
        return ""

    # remove typing generics
    sig = re.sub(r"\[[^\]]*\]", "", sig)

    # remove return type hints
    sig = re.sub(r"->.*", "", sig)

    params = []

    for part in sig.split(","):
        part = part.strip()

        if not part:
            continue

        # remove typing
        part = re.sub(r":.*", "", part)

        # remove default value
        part = re.sub(r"=.*", "", part)

        part = part.strip()

        # ignore invalid tokens
        if (
            part
            and part != "self"
            and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", part)
        ):
            params.append(part)

    return ", ".join(params)


def find_class(nid, parent, nodes):
    """Resolve enclosing class of a node."""
    while nid:
        if nodes.get(nid, {}).get("kind") == "class":
            return nid
        nid = parent.get(nid)
    return None


def to_mermaid(nodes: Dict[str, dict], edges: List[Tuple[str, str, str]]) -> str:
    parent: Dict[str, str] = {}

    for src, tgt, rel in edges:
        if rel == "contains":
            parent[tgt] = src

    classes: Dict[str, str] = {}
    methods: Dict[str, List[str]] = {}
    method_sig: Dict[str, str] = {}

    for nid, info in nodes.items():
        if info["kind"] == "class":
            classes[nid] = info["name"]

        elif info["kind"] == "method":
            method_sig[nid] = info.get("signature", "")
            p = parent.get(nid)

            if p:
                methods.setdefault(p, []).append(nid)

    lines = ["```mermaid", "classDiagram"]

    for cid, cname in sorted(classes.items(), key=lambda kv: kv[1]):
        lines.append(f"class {safe_name(cname)} {{")

        for mid in sorted(methods.get(cid, []), key=lambda x: nodes[x]["name"]):
            mname = nodes[mid]["name"]

            if not SHOW_PRIVATE and mname.startswith("_"):
                continue

            sig = simplify_signature(method_sig.get(mid, ""))

            if sig:
                lines.append(f"    +{mname}({sig})")
            else:
                lines.append(f"    +{mname}()")

        lines.append("}")

    inheritance = set()

    for src, tgt, rel in edges:
        if rel == "inherits" and src in classes and tgt in classes:
            lines.append(
                f"{safe_name(classes[tgt])} <|-- {safe_name(classes[src])}"
            )
            inheritance.add((src, tgt))

    seen = set()

    for src, tgt, rel in edges:
        if rel not in ("calls", "references", "imports", "creates"):
            continue

        cls_src = find_class(src, parent, nodes)
        cls_tgt = find_class(tgt, parent, nodes)

        if not cls_src or not cls_tgt:
            continue

        if cls_src == cls_tgt:
            continue

        if cls_src not in classes or cls_tgt not in classes:
            continue

        if (cls_src, cls_tgt) in inheritance or (cls_tgt, cls_src) in inheritance:
            continue

        pair = (cls_src, cls_tgt)

        if pair not in seen:
            lines.append(
                f"{safe_name(classes[cls_src])} --> {safe_name(classes[cls_tgt])}"
            )
            seen.add(pair)

    lines.append("```")

    return "\n".join(lines)


def main():
    input_path = Path("output/filescan_merged.csv")
    output_path = Path("output/filescan_uml.md")

    global SHOW_PRIVATE
    SHOW_PRIVATE = True

    nodes, edges = load_merged(input_path)

    uml = to_mermaid(nodes, edges)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write("# Filescan UML\n\n")
        f.write(uml)
        f.write("\n")

    print(f"UML written to: {output_path}")


if __name__ == "__main__":
    main()