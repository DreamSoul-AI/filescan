# filescan

**filescan** 是一个轻量级的 Python 工具，用于 **扫描文件系统结构和 Python AST（抽象语法树）**，并将结果导出为 **扁平化的图结构表示（flat graph）**。

不同于传统的嵌套树结构，`filescan` 会生成 **带有父指针（`parent_id`）的稳定节点列表**，使得输出结果：

* 易于后处理和二次分析
* 适合 CSV / DataFrame / SQL 等数据管道
* 对 LLM（大模型）上下文窗口非常友好，便于理解和总结

`filescan` 支持两种扫描层级：

* **文件系统结构扫描**（目录与文件）
* **Python 语义结构扫描（AST）**（模块、类、函数、方法）

两种扫描方式都采用相同的扁平图设计和统一的导出格式。

---

## 特性

### 文件系统扫描

* 递归遍历目录结构
* 使用显式 `parent_id` 的扁平节点列表
* 确定性排序（结果稳定可复现）
* 支持 `.gitignore` 风格的忽略规则
* 支持 CSV 和 JSON 导出

### Python AST 扫描

* 识别模块、类、函数和方法
* 支持嵌套函数与嵌套类
* 使用稳定的符号 ID 和父子关系
* 函数签名的“尽力而为”静态提取
* 提取 docstring 的首行作为说明

### 通用特性

* 统一的 schema 与导出模型
* 文件系统扫描与 AST 扫描使用相同的 API
* 既可作为 **Python 库** 使用，也可作为 **CLI 工具** 使用
* 面向自动化、数据管道和 AI / LLM 工作流设计

---

## 安装

```bash
pip install filescan
```

开发模式安装：

```bash
pip install -e .
```

---

## 快速开始（CLI）

### 文件系统扫描（默认）

扫描当前目录并生成 CSV：

```bash
filescan
```

扫描指定目录：

```bash
filescan ./data
```

导出为 JSON：

```bash
filescan ./data --format json
```

指定输出文件基名：

```bash
filescan ./data -o out/tree
```

将生成：

```text
out/
├── tree.csv
└── tree.json
```

---

### Python AST 扫描

扫描 Python 源码并提取语义符号：

```bash
filescan ./src --ast
```

以 JSON 格式导出 AST 符号：

```bash
filescan ./src --ast --format json
```

自定义输出路径：

```bash
filescan ./src --ast -o out/symbols
```

将生成：

```text
out/
├── symbols.csv
└── symbols.json
```

---

## 忽略规则（`.fscanignore`）

`filescan` 通过 `pathspec` 支持 **gitignore 风格的忽略规则**。

### 默认行为

* 如果指定了 `--ignore-file` → 使用该文件
* 否则自动查找：

```text
./.fscanignore   （当前工作目录）
```

忽略规则同时作用于：

* 文件系统扫描
* AST 扫描（被忽略的 Python 文件不会被解析）

### 示例 `.fscanignore`

```gitignore
.git/
.idea/
build/
dist/
__pycache__/
*.pyc
```

---

## 输出格式

文件系统扫描和 AST 扫描都会生成 **带 schema 描述的扁平图结构**。

---

### 文件系统 Schema

| 字段名         | 含义说明                  |
| ----------- | --------------------- |
| `id`        | 唯一整数 ID               |
| `parent_id` | 父节点 ID（根节点为 `null`）   |
| `type`      | `'d'` = 目录，`'f'` = 文件 |
| `name`      | 文件或目录名                |
| `size`      | 文件大小（字节；目录为 `null`）   |

#### CSV 示例

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

---

### Python AST Schema

| 字段名           | 含义说明                                       |
| ------------- | ------------------------------------------ |
| `id`          | 唯一符号 ID                                    |
| `parent_id`   | 父符号 ID（模块为 `null`）                         |
| `kind`        | `module` | `class` | `function` | `method` |
| `name`        | 符号名称                                       |
| `module_path` | 相对于扫描根目录的文件路径                              |
| `lineno`      | 起始行号（从 1 开始）                               |
| `signature`   | 函数 / 方法签名（尽力而为）                            |
| `doc`         | docstring 的第一行（如存在）                        |

嵌套函数、嵌套类通过 `parent_id` 自然表达，无需额外字段。

---

## 作为库使用

### 文件系统扫描

```python
from filescan import Scanner

scanner = Scanner(
    root="data",
    ignore_file=".fscanignore",
)

scanner.scan()
scanner.to_csv()    # -> ./data.csv
scanner.to_json()   # -> ./data.json
```

---

### Python AST 扫描

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

### 编程式访问

```python
nodes = scanner.scan()
print(len(nodes))

data = scanner.to_dict()
```

---

## 为什么选择 `filescan`？

大多数文件系统和代码结构通常以深度嵌套的树形式存储。虽然这种形式对人类友好，但在大规模处理时存在明显问题：

* 结构冗长
* 难以查询
* 不利于自动化与 AI 处理

`filescan` 使用 **扁平图结构（flat graph）** 来表示文件系统和代码库，因为这种形式：

* **紧凑、token 友好**
  数字 ID 的扁平列表相比递归树结构显著减少 token 数量，非常适合 LLM 上下文窗口。

* **明确、无歧义**
  所有父子关系通过 `parent_id` 显式表示。

* **易于处理**
  天然适合过滤、连接、分组、图分析等操作。

因此，`filescan` 非常适合用于：

* SQL / Pandas / DuckDB 数据分析
* 静态分析与代码重构工具
* 基于图的代码理解
* **基于大模型的项目理解与总结**

一句话总结：
`filescan` 选择 **机器友好** 的结构，而不是仅供人类浏览的目录树，从而支持可扩展的 AI 原生工作流。

---

## 开发说明

项目采用 `src/` 目录结构。

无需安装即可运行示例：

```bash
python examples/scan_data.py
```

或以模块方式运行：

```bash
python -m examples.scan_data
```

---

## License

MIT License

