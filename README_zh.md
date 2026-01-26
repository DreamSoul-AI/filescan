# filescan

**filescan** 是一个轻量级的 Python 工具，用于**递归扫描目录结构**，并将其导出为**扁平化的图结构表示**。

与传统的嵌套树结构不同，`filescan` 输出的是**带有父节点指针的稳定节点列表**，从而使结果：

* 易于后处理
* 对 CSV / DataFrame / SQL 管道非常友好
* 对 LLM 输入与结构理解更高效

## 功能特性

* 递归遍历目录结构
* 扁平化节点列表，显式 `parent_id` 关系
* 确定性（可复现）的节点顺序
* 支持 `.gitignore` 风格的忽略规则
* 支持 CSV 和 JSON 导出
* **既可作为库使用，也可作为 CLI 工具**
* 面向自动化、数据管道与 AI 工作流设计

## 安装

```bash
pip install filescan
```

开发模式安装：

```bash
pip install -e .
```

## 快速开始（CLI）

扫描当前目录并输出 CSV（默认）：

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

指定输出路径：

```bash
filescan ./data -o out/tree.csv
filescan ./data --format json -o out/tree.json
```

## 忽略规则（`.fscanignore`）

`filescan` 通过 `pathspec` 支持 **gitignore 风格的忽略模式**。

### 默认行为

* 如果显式指定 `--ignore-file` → 使用该文件
* 否则会尝试查找：

```text
./.fscanignore   （当前工作目录）
```

### 示例 `.fscanignore`

```gitignore
.git/
.idea/
build/
dist/
__pycache__/
*.pyc
```

## 输出格式

### 数据结构（Schema）

每个节点遵循如下结构：

| 字段          | 说明                    |
| ----------- | --------------------- |
| `id`        | 唯一整数 ID               |
| `parent_id` | 父节点 ID（根节点为 `null`）   |
| `type`      | `'d'` = 目录，`'f'` = 文件 |
| `name`      | 文件或目录的名称（basename）    |
| `size`      | 文件大小（字节），目录为 `null`   |

### CSV 输出（默认）

```csv
# id: 当前节点的唯一整数 ID
# parent_id: 父节点 ID，根节点为 null
# type: 节点类型：'d' = 目录，'f' = 文件
# name: 文件或目录名
# size: 文件大小（字节），目录为 null
id,parent_id,type,name,size
0,,d,data,
1,0,f,example.txt,128
```

### JSON 输出

```json
{
  "root": "/abs/path/to/data",
  "schema": [
    {"name": "id", "description": "唯一整数 ID"},
    {"name": "parent_id", "description": "父节点 ID（根节点为 null）"},
    {"name": "type", "description": "节点类型：'d' = 目录，'f' = 文件"},
    {"name": "name", "description": "文件或目录名"},
    {"name": "size", "description": "文件大小（字节），目录为 null"}
  ],
  "nodes": [
    [0, null, "d", "data", null],
    [1, 0, "f", "example.txt", 128]
  ]
}
```

## 作为库使用

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

### 自定义输出路径

```python
scanner.to_csv("out/tree.csv")
scanner.to_json("out/tree.json")
```

### 程序化访问

```python
nodes = scanner.scan()
print(len(nodes))

data = scanner.to_dict()
```

## 为什么使用 `filescan`？

大多数目录结构通常以**深度嵌套的树结构**表示。虽然对人类友好，但在以下方面存在明显不足：

* 结构冗长
* 查询困难
* 不适合大规模数据处理或 AI 输入

`filescan` 将文件系统表示为**扁平图结构**，原因在于：

* **更紧凑、更省 token**

  使用整数 ID 的扁平列表比递归嵌套结构消耗更少 token，非常适合 LLM 的上下文窗口。

* **关系显式、无歧义**

  父子关系通过 `parent_id` 明确表达，而不是依赖缩进或层级嵌套。

* **易于处理**

  扁平结构天然适合过滤、连接（join）和分组（group by）操作。

因此，`filescan` 特别适合以下场景：

* SQL / Pandas 数据管道
* 图分析与目录快照差分
* **基于 LLM 的文件结构理解与摘要**

简而言之，`filescan` 选择了**机器友好的结构，而非可视化树形展示**，以支持可扩展的数据分析与 AI 原生工作流。

## 开发说明

项目采用 `src/` 目录布局。

示例可在无需安装的情况下直接运行：

```bash
python examples/scan_data.py
```

或以模块方式运行：

```bash
python -m examples.scan_data
```

## 许可证

MIT License
