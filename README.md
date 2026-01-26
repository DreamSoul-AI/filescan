# filescan

**filescan** is a lightweight Python tool for **recursively scanning directory structures** and exporting them as a **flat, graph-style representation**.

Instead of nested trees, `filescan` produces a **stable list of nodes with parent pointers**, making the output:

* easy to post-process
* friendly for CSV / DataFrame / SQL pipelines
* efficient for LLM ingestion and summarization



## Features

* Recursive directory traversal
* Flat node list with explicit `parent_id`
* Deterministic ordering
* Optional `.gitignore`-style filtering
* CSV and JSON export
* Usable as **both a library and a CLI**
* Designed for automation, data pipelines, and AI workflows



## Installation

```bash
pip install filescan
```

Or for development:

```bash
pip install -e .
```



## Quick start (CLI)

Scan the current directory and write a CSV:

```bash
filescan
```

Scan a specific directory:

```bash
filescan ./data
```

Export as JSON:

```bash
filescan ./data --format json
```

Specify output path:

```bash
filescan ./data -o out/tree.csv
filescan ./data --format json -o out/tree.json
```



## Ignore rules (`.fscanignore`)

`filescan` supports **gitignore-style patterns** via `pathspec`.

### Default behavior

* If `--ignore-file` is provided → use it
* Otherwise, look for:

```text
./.fscanignore   (current working directory)
```

### Example `.fscanignore`

```gitignore
.git/
.idea/
build/
dist/
__pycache__/
*.pyc
```



## Output format

### Schema

Each node follows this schema:

| Field       | Description                                 |
| -- | - |
| `id`        | Unique integer ID                           |
| `parent_id` | Parent node ID (`null` for root)            |
| `type`      | `'d'` = directory, `'f'` = file             |
| `name`      | Base name                                   |
| `size`      | File size in bytes (`null` for directories) |



### CSV output (default)

```csv
# id: Unique integer ID for this node
# parent_id: ID of parent node, or null for root
# type: Node type: 'd' = directory, 'f' = file
# name: Base name of the file or directory
# size: File size in bytes; null for directories
id,parent_id,type,name,size
0,,d,data,
1,0,f,example.txt,128
```



### JSON output

```json
{
  "root": "/abs/path/to/data",
  "schema": [
    {"name": "id", "description": "Unique integer ID for this node"},
    {"name": "parent_id", "description": "ID of parent node, or null for root"},
    {"name": "type", "description": "Node type: 'd' = directory, 'f' = file"},
    {"name": "name", "description": "Base name of the file or directory"},
    {"name": "size", "description": "File size in bytes; null for directories"}
  ],
  "nodes": [
    [0, null, "d", "data", null],
    [1, 0, "f", "example.txt", 128]
  ]
}
```



## Library usage

```python
from pathlib import Path
from filescan import Scanner

scanner = Scanner(
    root="data",
    ignore_file=".fscanignore"
)

scanner.scan()

scanner.to_csv()    # -> ./data.csv
scanner.to_json()   # -> ./data.json
```

### Custom output paths

```python
scanner.to_csv("out/tree.csv")
scanner.to_json("out/tree.json")
```

### Programmatic access

```python
nodes = scanner.scan()
print(len(nodes))

data = scanner.to_dict()
```


## Why `filescan`?

Most directory trees are stored as deeply nested structures. While human-readable, they are verbose, hard to query, and inefficient for large-scale processing.

`filescan` represents a filesystem as a **flat graph** because it is:

* **Compact and token-efficient**
  A flat list with numeric IDs uses far fewer tokens than recursive trees, making it suitable for LLM context windows.

* **Explicit and unambiguous**
  Parent–child relationships are encoded directly via `parent_id`, without relying on nesting or indentation.

* **Easy to process**
  Flat data works naturally with filtering, joins, and grouping.

This design makes `filescan` especially suitable for:

* SQL and Pandas pipelines
* Graph analysis and snapshot diffing
* **LLM-based understanding and summarization of file structures**

In short, `filescan` favors **machine-friendly structure over visual trees**, enabling scalable analysis and AI-native workflows.




## Development

Project uses a `src/` layout.

Examples can be run without installation:

```bash
python examples/scan_data.py
```

Or as a module:

```bash
python -m examples.scan_data
```



## License

MIT License
