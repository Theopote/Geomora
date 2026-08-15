# Geomora 技术架构与开发手册 v0.1

**Project:** Geomora  
**Version:** v0.1  
**Stage:** Architecture Baseline / Phase 0  
**Primary Platform:** SketchUp Desktop  
**Primary Language:** Ruby + TypeScript + Python  
**Document Status:** Development Baseline

---

# 0. 文档目的

本文档定义 Geomora 的：

- 产品定位
- 技术边界
- 核心架构
- Architectural IR
- SketchUp Geometry Kernel
- 模块职责
- 数据流
- 测试原则
- 开发阶段
- Phase 0 实施范围
- 后续 AI 接入规则

从本版本开始，Geomora 的开发必须遵循本文档定义的架构。

除非经过明确的架构版本升级，否则不得为了短期 Demo：

- 绕过 IR 直接生成 SketchUp 几何；
- 让视觉模型直接调用 SketchUp Ruby API；
- 将 AI 模型输出格式与 SketchUp 实现绑定；
- 将业务逻辑大量写进 HtmlDialog；
- 将 Ruby、AI、UI、数据模型混成单体结构；
- 提前实现尚未进入当前 Phase 的功能。

---

# 1. Geomora 是什么

## 1.1 产品定义

Geomora 是一套运行于 SketchUp 工作流中的：

> **AI-assisted Architectural Geometry Reconstruction System**

其核心任务不是生成视觉上逼真的 Mesh，而是：

> **将不规则、噪声化、非结构化的现实信息转化为干净、合理、可编辑、具有建筑语义的几何模型。**

Geomora 的长期目标不是：

> Photo → Mesh

而是：

> Reality → Architectural Understanding → Editable Geometry

因此 Geomora 的技术核心不是某一个视觉模型。

真正的核心资产是：

1. Architectural IR
2. Architectural Understanding
3. Constraint Graph
4. Geometry Rationalization Engine
5. SketchUp Native Geometry Generator

原始讨论已经明确提出从“逼真网格”转向“几何理性化拟合”，并重点考虑语义分割、尺度标定、Manhattan World 与分层 LOD；这些原则继续保留。

---

# 2. 核心产品原则

Geomora 的开发遵循以下原则。

## P1. 输入可以脏，输出必须干净

输入可能包含：

- 透视变形
- 遮挡
- 杂物
- 树木
- 管线
- 广告牌
- 光影
- 模糊
- 扫描误差
- Mesh 噪声
- 点云误差

Geomora 输出不应机械复制这些噪声。

输出应该尽可能恢复：

> 建筑设计意图。

---

## P2. Architecture First

系统优先认识：

- Building
- Storey
- Wall
- Opening
- Window
- Door
- Floor
- Roof
- Column
- Beam
- Stair
- Balcony
- Component

而不是：

- triangle
- polygon soup
- anonymous mesh

---

## P3. Semantic Geometry > Raw Geometry

每个主要对象必须同时拥有：

```text
geometry
semantic
relationship
constraint
confidence
source
```

而不是只保存坐标。

---

## P4. AI proposes, Solver decides

AI 可以提出：

```text
这里可能是一扇窗
confidence = 0.87
```

但不能直接成为最终模型。

完整过程：

```text
AI Perception
      ↓
Candidate Geometry
      ↓
Constraint Graph
      ↓
Geometry Rationalization
      ↓
Validated Architectural IR
      ↓
SketchUp Geometry
```

---

## P5. Native SketchUp Geometry

最终输出优先使用：

- Edge
- Face
- Group
- ComponentDefinition
- ComponentInstance
- Material
- Tag

不得默认输出巨大三角 Mesh。

原稿也明确要求输出 SketchUp 原生几何并通过 Component 实现重复构件复用。

---

## P6. Human-in-the-loop

Geomora 不追求：

```text
Upload → Black Box → Finished Model
```

而追求：

```text
Detect
↓
Explain
↓
Preview
↓
Correct
↓
Rationalize
↓
Generate
```

用户可以修改：

- 类型
- 尺寸
- 约束
- 比例
- 重复模式
- 楼层
- 对齐关系
- 置信度较低结果

---

## P7. Deterministic Geometry

相同 IR 输入必须尽量得到相同几何输出。

不得让 SketchUp Geometry Generator 依赖随机 AI 行为。

---

# 3. 产品长期能力边界

Geomora 最终可以支持六类输入。

## 3.1 Photo

```text
Photo
→ Architectural Reconstruction
→ SketchUp
```

## 3.2 Multi-view Photo

```text
Multiple Photos
→ Camera / Geometry Fusion
→ Building Model
```

## 3.3 Point Cloud

```text
Point Cloud
→ Plane / Element Understanding
→ Architectural Model
```

## 3.4 Mesh

```text
Messy Mesh
→ Rationalization
→ Clean Architecture
```

## 3.5 Drawing

```text
Plan / Elevation / Scan
→ Architectural Geometry
```

## 3.6 Existing SketchUp Model

```text
Messy SketchUp Model
→ Geometry Doctor
→ Rationalized Model
```

---

# 4. 三个长期产品模式

未来 Geomora 可以形成三个一级工作模式。

```text
Geomora
│
├── Reconstruct
│   Reality → Architecture
│
├── Rationalize
│   Messy Geometry → Clean Geometry
│
└── Generate
    Intent → Architecture
```

Phase 0 不实现这三个完整功能。

Phase 0 只建立支持它们的底层架构。

---

# 5. 总体系统架构

```text
┌────────────────────────────────────────┐
│              GEOMORA                   │
└────────────────────────────────────────┘

                INPUT

Photo / Video / Scan / Mesh / Point Cloud
                │
                ▼

┌────────────────────────────────────────┐
│ Layer 1 — Capture & Input              │
└────────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────┐
│ Layer 2 — Perception                   │
│                                        │
│ Segmentation                           │
│ Line Detection                         │
│ Depth                                  │
│ Vanishing Point                        │
│ Feature Matching                       │
└────────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────┐
│ Layer 3 — Architectural Understanding  │
│                                        │
│ Wall / Window / Door                   │
│ Floor / Roof / Column                  │
│ Storey                                 │
│ Pattern / Topology                     │
└────────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────┐
│ Layer 4 — Geometry Rationalization     │
│                                        │
│ Plane Fitting                          │
│ Snapping                               │
│ Orthogonalization                      │
│ Constraint Solving                     │
│ Symmetry                               │
│ Repetition                             │
│ Dimension Normalization                │
└────────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────┐
│ Layer 5 — Geomora Architectural IR     │
└────────────────────────────────────────┘
                │
       ┌────────┼─────────┐
       ▼        ▼         ▼
   SketchUp    IFC      Future
   Generator  Export    Adapter
```

---

# 6. 模块边界

## 6.1 Plugin

负责：

- SketchUp Extension 生命周期
- 菜单
- Toolbar
- HtmlDialog
- Model Operation
- Geometry Generation
- Component Management
- Tag Management
- Selection
- Undo / Redo
- 本地 Backend 通信

不负责：

- AI inference
- 深度估计
- 大型矩阵计算
- CV pipeline
- AI model management

---

## 6.2 Frontend

负责：

- Workspace
- Image Viewer
- Element Tree
- Property Inspector
- Reconstruction Preview
- 用户修正
- 状态显示
- 错误提示

技术：

```text
TypeScript
React
Vite
```

通过 HtmlDialog 运行。

---

## 6.3 Backend

未来负责：

```text
Vision
Understanding
Geometry
Solver
IR Validation
Pipeline
```

技术：

```text
Python
FastAPI
Pydantic
NumPy
OpenCV
PyTorch
SciPy
```

Phase 0 不要求启动 AI Backend。

---

# 7. 核心：Geomora Architectural IR

## 7.1 为什么必须有 IR

Architectural IR 是 Geomora 最重要的数据契约。

所有系统：

```text
Vision
Solver
SketchUp
Future IFC
Future Rhino
```

都通过 IR 解耦。

严禁：

```text
SAM output
→ Ruby API
```

应该：

```text
SAM
↓
Understanding
↓
Architectural IR
↓
SketchUp Adapter
```

原讨论稿已经设计了包含 unit、wall thickness、walls、openings 和 roof polygon 的 JSON；v0.1 将其正式升级为 Architectural IR。

---

# 8. IR 顶层结构

建议 v0.1：

```json
{
  "schema_version": "0.1",

  "project": {},

  "buildings": [],

  "components": [],

  "constraints": [],

  "sources": []
}
```

---

# 9. Project

```json
{
  "id": "project_001",
  "name": "Example Project",
  "unit": "mm",
  "coordinate_system": "z_up",
  "default_wall_thickness": 240
}
```

要求：

- 内部统一使用 mm；
- SketchUp Adapter 负责单位换算；
- 不允许业务对象自行判断英制/公制。

---

# 10. Building

```json
{
  "id": "building_001",
  "name": "Main Building",
  "storeys": []
}
```

---

# 11. Storey

```json
{
  "id": "storey_01",

  "name": "Ground Floor",

  "elevation": 0,

  "height": 3300,

  "elements": []
}
```

---

# 12. Wall

建议使用 baseline 驱动，而不是直接保存任意 Mesh。

```json
{
  "id": "wall_001",

  "type": "wall",

  "storey_id": "storey_01",

  "geometry": {
    "baseline": [
      [0, 0, 0],
      [10000, 0, 0]
    ],

    "height": 3300,

    "thickness": 240
  },

  "semantic": {
    "exterior": true
  },

  "opening_ids": [
    "window_001",
    "window_002",
    "door_001"
  ],

  "confidence": 1.0
}
```

---

# 13. Opening

Opening 是逻辑抽象类。

实现类型：

```text
Window
Door
GenericOpening
```

---

# 14. Window

```json
{
  "id": "window_001",

  "type": "window",

  "parent_id": "wall_001",

  "geometry": {
    "offset": 1200,
    "sill_height": 900,
    "width": 1500,
    "height": 1500,
    "depth": 240
  },

  "component": {
    "definition_id": "window_standard_1500"
  },

  "confidence": 1.0
}
```

---

# 15. Door

```json
{
  "id": "door_001",

  "type": "door",

  "parent_id": "wall_001",

  "geometry": {
    "offset": 7000,
    "width": 900,
    "height": 2100,
    "depth": 240
  }
}
```

---

# 16. Roof

Phase 0 只定义 Schema，不要求完整生成器。

```json
{
  "id": "roof_001",

  "type": "roof",

  "geometry": {
    "polygon": [],
    "elevation": 3300
  }
}
```

---

# 17. ComponentDefinition

```json
{
  "id": "window_standard_1500",

  "type": "window",

  "parameters": {
    "width": 1500,
    "height": 1500
  }
}
```

目标：

```text
One Definition
+
Many Instances
```

而不是复制几何。

---

# 18. Constraint Schema

虽然 Phase 0 不实现 Solver，但 IR 必须预留约束。

```json
{
  "id": "constraint_001",

  "type": "equal_width",

  "targets": [
    "window_001",
    "window_002",
    "window_003"
  ],

  "priority": "hard"
}
```

支持的预留类型：

```text
parallel
perpendicular
coplanar
horizontal
vertical
equal_width
equal_height
equal_spacing
symmetry
align
fixed_dimension
grid
```

---

# 19. Confidence

AI 产生的所有语义对象未来必须允许：

```json
{
  "confidence": 0.83
}
```

手动确定对象：

```text
confidence = 1.0
```

原则：

> confidence 属于推断结果，不属于最终几何本身。

---

# 20. Source Trace

对象未来应允许追踪来源。

```json
{
  "source": {
    "source_id": "photo_001",
    "region": [230, 120, 530, 460]
  }
}
```

方便：

- UI 回显
- AI Debug
- 用户修正
- 数据集积累

---

# 21. IR Validator

必须实现 Validator。

至少验证：

```text
schema_version
required fields
unique IDs
valid parent references
positive dimensions
valid wall baseline
opening inside wall
no duplicated IDs
supported units
```

原则：

> invalid IR 不得进入 SketchUp Geometry Generator。

---

# 22. SketchUp Geometry Kernel

Geometry Kernel 负责：

```text
Architectural IR
↓
SketchUp Native Geometry
```

必须与：

- AI
- Vision
- HTTP
- HtmlDialog

完全解耦。

---

# 23. Generator Architecture

推荐：

```text
Generator
│
├── ProjectGenerator
├── BuildingGenerator
├── StoreyGenerator
├── WallGenerator
├── OpeningGenerator
├── WindowGenerator
├── DoorGenerator
├── RoofGenerator
└── ComponentManager
```

---

# 24. Wall Generator

输入：

```text
baseline
height
thickness
```

生成：

```text
Group
└── Solid-like wall geometry
```

要求：

- 保持法线方向一致；
- 墙厚由 baseline 方向确定；
- 不允许出现零面积 Face；
- 不留下重复 Edge；
- 创建失败必须抛出明确错误。

---

# 25. Opening Generator

不得简单：

```text
wall
+
window mesh
```

必须真正形成：

> Wall Opening

Phase 0 可采用 SketchUp 原生几何布尔思路或稳定的面构造策略。

核心要求：

```text
Opening modifies wall geometry
```

窗口不是贴在墙外面的装饰矩形。

---

# 26. Component Manager

窗、门等可重复对象必须：

```text
ComponentDefinition
+
ComponentInstance
```

例如：

```text
Window_A
   ×4
```

不能生成：

```text
Window_1 geometry
Window_2 geometry
Window_3 geometry
Window_4 geometry
```

原稿同样把 Component Library 作为性能与可编辑性的关键策略。

---

# 27. Tag Strategy

Phase 0 预设：

```text
Geomora_Walls
Geomora_Windows
Geomora_Doors
Geomora_Roofs
Geomora_Reference
```

注意：

SketchUp 建模最佳实践中，基础 raw geometry 应保持合理的上下文管理。

主要分类应施加于：

```text
Group
ComponentInstance
```

而不是随意污染单个 Edge / Face。

---

# 28. Metadata

所有 Geomora 生成对象建议写入 AttributeDictionary：

```text
geomora
```

内容：

```text
entity_id
entity_type
schema_version
source_id
```

例如：

```text
geomora.entity_id = wall_001
```

未来可实现：

```text
SketchUp Entity
↕
Architectural IR
```

---

# 29. Transaction Management

任何一次完整生成必须包裹在：

```ruby
model.start_operation(...)
...
model.commit_operation
```

异常：

```ruby
model.abort_operation
```

必须支持：

```text
Ctrl + Z
```

一次撤销整个 Geomora 操作。

原讨论稿第 5、9、10 页也把 Transaction Management 和 Ctrl+Z 作为核心要求。

---

# 30. Idempotency

相同 project_id 重复生成时，不允许无限叠加重复模型。

Phase 0 至少必须明确策略。

推荐：

```text
Generate Mode:

Create New
Replace Existing Geomora Building
```

默认测试：

```text
Replace Existing
```

通过 AttributeDictionary 寻找已有对象。

---

# 31. Error Model

禁止：

```text
rescue Exception
end
```

吞掉异常。

定义：

```text
GeomoraError
IRValidationError
GeometryGenerationError
ReferenceError
UnsupportedSchemaError
```

UI 与日志显示用户可理解错误。

---

# 32. Logging

日志级别：

```text
DEBUG
INFO
WARN
ERROR
```

Phase 0 至少输出：

```text
Geomora initialized

IR loaded

Validation passed

Generating wall_001

Generating window_001

Generation completed
```

---

# 33. Phase 0 架构

Phase 0 唯一数据流：

```text
fixture.json
      ↓
IR Loader
      ↓
IR Validator
      ↓
Architecture Model
      ↓
SketchUp Generator
      ↓
Native SketchUp Model
```

没有：

```text
SAM
YOLO
Depth Anything
FastAPI
LLM
Cloud
WebSocket
Multi-view
```

---

# 34. Phase 0 Fixture

必须提供固定测试工程：

```text
Building width: 10000 mm

Wall height: 3300 mm

Wall thickness: 240 mm

Windows:
4

Window:
1500 × 1500

Sill:
900 mm

Door:
900 × 2100
```

示意：

```text
┌────────────────────────────────────────┐
│                                        │
│ ┌────┐  ┌────┐  ┌────┐  ┌────┐       │
│ │ W1 │  │ W2 │  │ W3 │  │ W4 │       │
│ └────┘  └────┘  └────┘  └────┘       │
│                              ┌──────┐  │
│                              │ Door │  │
└──────────────────────────────┴──────┴──┘
```

实际 offset 必须避免冲突。

---

# 35. Phase 0 Definition of Done

只有全部通过，Phase 0 才算完成。

## Architecture

- [ ] 插件可以加载
- [ ] 无 load error
- [ ] 模块边界清晰
- [ ] IR 与 SketchUp Generator 解耦

## IR

- [ ] schema_version
- [ ] project
- [ ] building
- [ ] storey
- [ ] wall
- [ ] window
- [ ] door
- [ ] component
- [ ] constraint schema
- [ ] validator

## Geometry

- [ ] 正确生成墙
- [ ] 正确墙厚
- [ ] 正确墙高
- [ ] 4 个真实窗洞
- [ ] 1 个真实门洞
- [ ] 没有明显重复 Face
- [ ] 没有错误几何残留

## Components

- [ ] 4 个窗使用同一个 ComponentDefinition
- [ ] 每个 Window 有独立 ComponentInstance
- [ ] Door 可独立定义

## Organization

- [ ] Group 合理
- [ ] Tag 合理
- [ ] AttributeDictionary 正确

## Units

- [ ] IR 内部单位统一 mm
- [ ] SketchUp 尺寸一致
- [ ] 不出现 ×25.4 错误

## Transaction

- [ ] Generate 为单事务
- [ ] Ctrl+Z 一次完全撤销

## Repeatability

连续运行：

```text
Generate
Generate
Generate
```

不得得到三个重叠 Building。

## Failure

非法 Fixture：

```text
negative thickness
invalid parent
duplicate id
opening outside wall
```

必须拒绝。

---

# 36. 自动测试

推荐：

```text
tests/
├── fixtures/
│   ├── facade_valid.json
│   ├── invalid_duplicate_id.json
│   ├── invalid_parent.json
│   └── invalid_dimension.json
│
├── ir/
├── geometry/
└── integration/
```

Ruby 单元测试重点测试：

```text
Validator
Unit conversion
Reference resolution
Component cache
Geometry helpers
```

SketchUp API 强依赖测试可通过 SketchUp 内 integration test 执行。

---

# 37. 推荐仓库结构

```text
geomora/
│
├── plugin/
│   │
│   ├── geomora.rb
│   │
│   └── geomora/
│       │
│       ├── extension.rb
│       │
│       ├── version.rb
│       │
│       ├── core/
│       │   ├── project.rb
│       │   ├── loader.rb
│       │   └── errors.rb
│       │
│       ├── ir/
│       │   ├── parser.rb
│       │   ├── validator.rb
│       │   └── models/
│       │
│       ├── generators/
│       │   ├── building_generator.rb
│       │   ├── storey_generator.rb
│       │   ├── wall_generator.rb
│       │   ├── opening_generator.rb
│       │   ├── window_generator.rb
│       │   └── door_generator.rb
│       │
│       ├── geometry/
│       │   ├── units.rb
│       │   ├── vectors.rb
│       │   └── polygon.rb
│       │
│       ├── components/
│       │   └── component_manager.rb
│       │
│       ├── metadata/
│       │   └── attributes.rb
│       │
│       ├── transactions/
│       │   └── operation.rb
│       │
│       └── ui/
│           └── commands.rb
│
├── frontend/
│   └── README.md
│
├── backend/
│   └── README.md
│
├── schemas/
│   └── geomora-ir-v0.1.schema.json
│
├── examples/
│   └── facade_phase0.json
│
├── tests/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── IR.md
│   └── PHASES.md
│
└── README.md
```

Phase 0：

```text
frontend/
backend/
```

可以仅作为 placeholder。

不得提前实现。

---

# 38. Phase 1 — Reconstruction Workspace

Phase 0 完成后再进入。

目标：

```text
SketchUp
+
HtmlDialog
+
Image
+
Manual Facade Definition
```

主要 UI：

```text
Sources
Image Viewer
Elements
Inspector
Generate
```

AI 仍可为空。

---

# 39. Phase 2 — Perspective Rectification

加入：

```text
Line Detection
Vanishing Point
Homography
Facade Rectification
```

目标：

```text
Perspective Photo
↓
Rectified Facade
```

---

# 40. Phase 3 — Semantic Reconstruction

加入：

```text
Wall
Window
Door
```

检测。

候选技术：

```text
SAM 2
YOLO
GroundingDINO
```

原讨论稿在视觉管线中也建议 SAM2 / YOLO 和语义分割作为主要入口。

---

# 41. Phase 4 — Geometry Rationalization

Geomora 真正的核心阶段。

实现：

```text
Snap
Align
Parallel
Perpendicular
Equal Size
Equal Spacing
Symmetry
Grid Detection
Dimension Normalization
```

建立：

> Constraint Graph

---

# 42. Phase 5 — Pattern Intelligence

实现：

```text
Translation Pattern
Grid Pattern
Mirror Pattern
Storey Repetition
Window Bay
Column Grid
```

自动生成 ComponentDefinition。

---

# 43. Phase 6 — Multi-view Reconstruction

再引入：

```text
Depth
Camera Pose
Feature Matching
Plane Fusion
```

候选技术：

```text
Depth Anything
Marigold
COLMAP
OpenCV
```

原稿第 6–7 页将这些工具安排在更完整的视觉与几何重建管线中；本手册保留这一方向，但推迟到基础几何链稳定之后。

---

# 44. Phase 7 — Full Building

支持：

```text
Floor
Roof
Column
Beam
Stair
Balcony
Parapet
Cornice
```

---

# 45. Phase 8 — Geometry Doctor

支持已有模型清理：

```text
Tiny Edge Detection
Coplanar Merge
Duplicate Geometry
Component Detection
Alignment Repair
Normal Repair
Opening Repair
```

---

# 46. LOD Strategy

继续采用：

```text
LOD 100
LOD 200
LOD 300
```

但定义为建筑语义 LOD。

## LOD 100

```text
Massing
Storey
Major Wall
Roof
```

## LOD 200

```text
Wall
Door
Window
Column
Balcony
```

## LOD 300

```text
Frame
Trim
Cornice
Railing
Eaves
Architectural Details
```

原讨论稿已经提出类似 LOD 100/200/300 分层，这是后续很值得保留的产品能力。

---

# 47. LLM 的职责

LLM 不负责最终坐标生成。

允许负责：

```text
Natural Language Command
Semantic Interpretation
Constraint Creation
Workflow Assistance
Explanation
```

例如：

```text
“把这些窗统一成 1500 宽。”
```

转成：

```json
{
  "operation": "set_dimension",
  "targets": ["window_group_01"],
  "property": "width",
  "value": 1500
}
```

---

# 48. 禁止的技术捷径

整个项目禁止以下做法。

## 禁止 1

```text
AI
→ raw mesh
→ SketchUp
```

作为核心流程。

## 禁止 2

AI 输出最终 SketchUp Ruby 代码。

## 禁止 3

Vision layer 直接访问 SketchUp API。

## 禁止 4

为了 Demo 将所有代码写在一个：

```text
main.rb
```

## 禁止 5

没有测试就开始多视图摄影测量。

## 禁止 6

Phase 0 接入：

```text
SAM
YOLO
LLM
Depth
FastAPI
```

## 禁止 7

将重复窗复制成独立 raw geometry。

## 禁止 8

无法一次 Undo。

## 禁止 9

吞异常。

## 禁止 10

代码“看起来能运行”就宣布 Phase 完成。

---

# 49. Phase Gate

任何 Phase 进入下一阶段前必须回答：

```text
1. 当前 Phase 的 Definition of Done 是否全部通过？
2. 是否存在阻塞下一阶段的架构债务？
3. 是否有测试保护？
4. 是否保持 IR 向后兼容？
5. 是否出现临时 hack？
6. 是否更新 docs？
```

只要存在核心问题：

> 不进入下一 Phase。

---

# 50. 当前开发决策

从 v0.1 开始正式确定：

### 决策 A

Geomora 使用 Architectural IR。

### 决策 B

IR 是系统唯一核心数据契约。

### 决策 C

Phase 0 不接 AI。

### 决策 D

SketchUp Generator 必须独立。

### 决策 E

内部长度统一使用 mm。

### 决策 F

输出优先 SketchUp 原生几何。

### 决策 G

重复构件必须使用 Component。

### 决策 H

Geomora 操作必须支持 SketchUp Undo。

### 决策 I

AI 只产生候选结果。

### 决策 J

Geometry Rationalization Engine 是长期核心技术。

---

# 51. Phase 0 最终目标

Phase 0 完成时，我们应该能够完全不依赖 AI，拿到：

```text
facade_phase0.json
```

然后：

```text
Geomora
→ Validate
→ Build
```

得到：

```text
SketchUp

Building
└── Ground Floor
    └── Wall
        ├── Window ×4
        └── Door ×1
```

其中：

- 尺寸正确；
- 墙体真实有洞；
- 窗口为 Component；
- 元数据存在；
- Tag 正确；
- 重复执行安全；
- Ctrl+Z 一次撤销；
- Invalid IR 会被拒绝。

只有完成这一件事：

> Geomora 才拥有真正可靠的“建筑几何地基”。

---

# 52. 当前下一步

立即执行：

> **Phase 0 — Architectural IR + SketchUp Geometry Kernel**

不要开始：

```text
AI
Image Recognition
Depth
LLM
Multi-view
Photogrammetry
```

直到 Phase 0 Gate 全部通过。

---

**Geomora v0.1 Architecture Principle**

> **Understand first. Rationalize second. Generate last.**

以及整个项目最核心的技术原则：

> **Geomora does not reconstruct pixels.  
> Geomora reconstructs architecture.**