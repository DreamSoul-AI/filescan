# filescan

**filescan** is a lightweight Python tool for scanning:

* 📁 **Filesystem structures**
* 🧠 **Python semantic structures (AST)**

and exporting them as **flat graph representations**.

Instead of deeply nested trees, `filescan` produces **stable node + edge lists**, making the output:

* Easy to query
* Friendly for CSV / SQL / Pandas workflows
* Efficient for LLM ingestion
* Suitable for graph analysis

Both filesystem and AST scanning use the same flat graph design.

---

# Why Flat Graphs?

Traditional tree structures are:

* Deeply nested
* Verbose
* Hard to filter
* Inefficient for large-scale processing
* Expensive for LLM token usage

`filescan` uses a flat graph model:

```
nodes.csv
edges.csv
```

Relationships are explicit via IDs, not nesting.

This makes it:

* Machine-friendly
* Query-friendly
* Token-efficient
* AI-native

---

# Features

## 📁 Filesystem Scanning

* Recursive directory traversal
* Deterministic ordering
* Explicit parent → child edges
* Optional `.gitignore`-style filtering
* CSV and JSON export
* Stable numeric IDs

## 🧠 Python AST Scanning

* Module detection
* Class detection
* Function & method detection
* Nested definitions supported
* Function signature extraction (best-effort)
* First-line docstring capture
* Cross-file semantic relationships:

  * `contains`
  * `imports`
  * `calls`
  * `inherits`
  * `references`

## ⚙ General

* Shared graph schema design
* Same API for filesystem and AST
* CLI + library usage
* Designed for automation and AI workflows

---

# Installation

```bash
pip install filescan
```

Development mode:

```bash
pip install -e .
```

---

# Quick Start (CLI)

## Filesystem Scan (Default)

Scan current directory:

```bash
filescan
```

Scan specific directory:

```bash
filescan ./data
```

Export JSON:

```bash
filescan ./data --format json
```

Custom output path:

```bash
filescan ./data -o out/tree
```

Output:

```
out/
├── tree_nodes.csv
└── tree_edges.csv
```

---

## Python AST Scan

Scan Python source files:

```bash
filescan ./src --ast
```

Export JSON:

```bash
filescan ./src --ast --format json
```

Custom output:

```bash
filescan ./src --ast -o out/symbols
```

Output:

```
out/
├── symbols_nodes.csv
└── symbols_edges.csv
```

---

# Ignore Rules (`.fscanignore`)

`filescan` supports **gitignore-style patterns** via `pathspec`.

### Resolution order:

1. `--ignore-file` if provided
2. `./.fscanignore` in working directory
3. Built-in default ignore rules

Ignore rules apply to:

* Filesystem scanning
* AST scanning (ignored Python files are skipped)

### Example `.fscanignore`

```gitignore
.git/
.idea/
build/
dist/
__pycache__/
*.pyc
```

---

# Output Format

Both scanners produce:

* `*_nodes.csv`
* `*_edges.csv`
* Optional JSON

Each file includes schema metadata as commented headers.

---

# Filesystem Graph Schema

## Nodes

| Field  | Description                                 |
| ------ | ------------------------------------------- |
| `id`   | Unique integer ID                           |
| `type` | `'d'` = directory, `'f'` = file             |
| `name` | Base filename                               |
| `size` | File size in bytes (`null` for directories) |

## Edges

| Field      | Description       |
| ---------- | ----------------- |
| `id`       | Unique edge ID    |
| `source`   | Parent node ID    |
| `target`   | Child node ID     |
| `relation` | Always `contains` |

---

# Python AST Graph Schema

## Nodes

| Field            | Description                             |
| ---------------- | --------------------------------------- |
| `id`             | Unique symbol ID                        |
| `kind`           | `module`, `class`, `function`, `method` |
| `name`           | Symbol name                             |
| `qualified_name` | Fully qualified symbol path             |
| `module_path`    | File path relative to scan root         |
| `lineno`         | Starting line (1-based)                 |
| `end_lineno`     | Ending line                             |
| `signature`      | Function signature                      |
| `doc`            | First line of docstring                 |

## Edges

| Relation     | Meaning                      |
| ------------ | ---------------------------- |
| `contains`   | Parent symbol contains child |
| `imports`    | Module imports symbol        |
| `calls`      | Function calls symbol        |
| `inherits`   | Class inherits from base     |
| `references` | Symbol references another    |

---

# Library Usage

## Filesystem Scanner

```python
from filescan import Scanner

scanner = Scanner(root="data")
scanner.scan()
scanner.to_csv()
scanner.to_json()
```

---

## Python AST Scanner

```python
from filescan import AstScanner

scanner = AstScanner(
    root="src",
    ignore_file=".fscanignore",
    output="out/symbols",
)

scanner.scan()
scanner.to_csv()
scanner.to_json()
```

---

## Programmatic Access

```python
nodes = scanner.scan()

print(len(nodes))
print(nodes[0])
```

---

# Designed for AI & Data Pipelines

`filescan` is especially useful for:

* LLM-based code understanding
* Token-efficient project summarization
* Static analysis
* Code graph generation
* SQL / Pandas / DuckDB pipelines
* Refactoring tools
* Cross-file semantic reasoning

Flat graphs are far more efficient than nested JSON trees when:

* Feeding into LLMs
* Performing joins
* Running graph algorithms
* Building embeddings

---

# Development

Project uses `src/` layout.

Run examples:

```bash
python examples/scan_data.py
```

Or:

```bash
python -m examples.scan_data
```

---

# License

MIT License

