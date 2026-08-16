# Geomora 立面 YOLO 标注指南

为 `yolo_v1` 检测器准备**真实建筑**训练数据。标注对象是 **Rectify 后的正立面图**，不是原始透视照片。

相关文档：

- 训练命令与验证：`docs/YOLO_TRAINING.md`
- 数据集目录：`backend/data/facade_yolo_custom/`

---

## 1. 标注什么

| Class ID | 名称 | 标注范围 |
|----------|------|----------|
| **0** | `window` | 窗洞可见区域（玻璃 / 窗扇），**尽量贴内缘，不含窗框外沿** |
| **1** | `door` | 门洞可见区域（门扇 / 玻璃门），**不含门框装饰线** |

**不要标注：**

- 未 Rectify 的原始透视图
- 空调外机、招牌、阴影、反光中的“假窗”
- 整面墙或整层幕墙外轮廓（只标单个开洞）

**推荐顺序：**

```text
Load Image → 调四角 → Rectify Facade →（可选）Detect 作参考 → 外部工具标框 → 放入 custom 数据集 → 重训
```

---

## 2. 获取待标注图片

Rectify 成功后，插件会把正立面图写入缓存：

| 环境 | 路径 |
|------|------|
| 开发（本仓库） | `plugin/geomora/cache/rectified_<时间戳>.jpg` |
| RBZ 安装后 | `%APPDATA%\SketchUp\SketchUp 20XX\SketchUp\Plugins\geomora\cache\` 下同名文件 |

操作步骤：

1. SketchUp → **Geomora Workspace**
2. **Load Image** → 拖动四角 → **Rectify Facade**
3. 到上述 `cache` 目录找到最新的 `rectified_*.jpg`
4. 复制到数据集目录，例如：

```text
backend/data/facade_yolo_custom/train/images/building_001.jpg
```

命名建议：`building_<序号>.jpg`，与 label 文件同名。

---

## 3. YOLO 标签格式

每个图片对应一个 `.txt`，**文件名 stem 必须一致**：

```text
train/images/building_001.jpg
train/labels/building_001.txt
```

每行一个框（空格分隔，**全部归一化到 0–1**）：

```text
<class_id> <cx> <cy> <w> <h>
```

示例：

```text
0 0.1625 0.3833 0.1500 0.3000
0 0.4125 0.3850 0.1500 0.2980
1 0.0500 0.7417 0.0750 0.3833
```

含义：

- `cx`, `cy`：框中心（相对图片宽/高）
- `w`, `h`：框宽/高（相对图片宽/高）
- 坐标原点：左上角；Y 轴向下（与 OpenCV / Geomora 一致）

### 与 Geomora `bbox_norm` 的换算

Workspace 检测/Overlay 使用 `[x_min, y_min, x_max, y_max]`（0–1）。转为 YOLO：

```text
cx = (x_min + x_max) / 2
cy = (y_min + y_max) / 2
w  = x_max - x_min
h  = y_max - y_min
```

示例：`bbox_norm = [0.10, 0.23, 0.25, 0.53]` → `0 0.175 0.38 0.15 0.30`

---

## 4. 目录结构

```text
backend/data/facade_yolo_custom/
  train/
    images/
      building_001.jpg
      building_002.jpg
    labels/
      building_001.txt
      building_002.txt
  val/
    images/
      building_010.jpg
    labels/
      building_010.txt
```

规则：

- **train / val 分开**；建议约 **80% / 20%**
- 每个 split 下 `images/` 与 `labels/` 一一对应
- 支持 `.jpg` / `.jpeg` / `.png` / `.webp`
- 无目标的图片：**不写 txt**，或写空文件（不建议大量空图）

---

## 5. 推荐标注工具

### 方案 A：LabelImg（本地，最适合 YOLO）

**安装（Windows）：**

```powershell
pip install labelImg
labelImg
```

若 `labelImg` 命令不可用，可尝试：

```powershell
python -m labelImg
```

**首次配置：**

1. **Open Dir** → 选择 `train/images`（或 `val/images`）
2. **Change Save Dir** → 选择对应的 `train/labels`（或 `val/labels`）
3. 左下角格式选 **YOLO**（不是 PascalVOC）
4. **View → Auto Save mode**（推荐开启）
5. 创建类别文件 `predefined_classes.txt`（与图片同目录或 LabelImg 提示处）：

```text
window
door
```

**快捷键：**

| 键 | 作用 |
|----|------|
| `W` | 画框 |
| `D` | 下一张 |
| `A` | 上一张 |
| `Del` | 删除当前框 |
| `Ctrl+S` | 保存 |

**注意：** LabelImg 按 `predefined_classes.txt` 行号生成 class id（第一行 = 0）。务必让 **window = 0、door = 1**，与 Geomora 一致。

---

### 方案 B：makesense.ai（浏览器，免安装）

适合快速试标几张图。

1. 打开 [https://www.makesense.ai](https://www.makesense.ai)
2. **Get Started** → 拖入 `train/images` 中的图片
3. 添加 Labels：`window`、`door`（顺序同上）
4. 框选开洞区域
5. **Actions → Export Annotations** → 格式选 **YOLO**
6. 解压后将 `.txt` 放入 `train/labels/`，并核对文件名与图片一致

---

### 方案 C：CVAT / Roboflow（团队协作）

| 工具 | 适用场景 |
|------|----------|
| [CVAT](https://www.cvat.ai) | 多人审核、任务分配、版本管理 |
| [Roboflow](https://roboflow.com) | 在线增强 + 导出 YOLOv8 数据集 |

导出时选择 **YOLO Darknet / YOLO 1.1** 格式，class 顺序仍为 `window`(0)、`door`(1)，再放入 `facade_yolo_custom/`。

---

## 6. Workspace 一键导出（推荐）

Geomora Workspace 可直接把 **Overlay 上的框** 导出为 YOLO 数据集，无需在外部工具里重复标框。

**步骤：**

1. **Load Image** → 调四角 → **Rectify Facade**
2. **Detect Elements**（或 **Draw window** 手动画框）→ 在 **Overlay** 视图校正框
3. 选择 **train** 或 **val**
4. 点击 **Export YOLO Labels**
5. 在文件夹对话框中选择数据集根目录（默认建议 `backend/data/facade_yolo_custom`）
6. 确认状态栏成功消息中的 `images/` 与 `labels/` 路径

**导出内容：**

- 复制当前 rectified 图片 → `{dataset}/{split}/images/<stem>.jpg`
- 由 Overlay 框生成 YOLO txt → `{dataset}/{split}/labels/<stem>.txt`
- class 0 = window，class 1 = door（与上文一致）
- 仅导出**首层**开洞（训练立面检测用）；门仅在 **Door width > 0** 时导出

**典型迭代：**

```text
Detect → Overlay 删误检/补漏检 → Export (train) × N 张
→ 挑 2–3 张 Export (val) → train_yolo_facade.py → 再 Detect 验证
```

---

## 7. 用 Geomora Workspace 辅助（外部工具对照）

若使用 LabelImg 等外部工具，仍可用 Workspace Overlay 作**视觉参考**（当前不会自动同步到 LabelImg 项目）：

1. **Rectify** 后 **Detect Elements**（Auto / YOLO / Facade row）
2. 切换到 **Rectified** 或 **Overlay** 视图
3. 用 Overlay 工具微调：
   - **Draw window**：拖拽新建窗框
   - 点击框选中 → 拖角点缩放 / 拖动平移
   - **Delete selected**：删除误检
   - 门：在 Inspector 填写 **Door width > 0** 后才会显示门框
4. 对照 Overlay 上的框，在 LabelImg 里标到**同一位置**（或按第 3 节公式从 `bbox_norm` 手算 YOLO 行）

这样可以把自动检测当作“初稿”；**优先用第 6 节一键导出**，外部工具适合批量精修或团队审核。

---

## 8. 标注质量检查清单

标完一批后，逐项核对：

- [ ] 图片已是 **Rectify 后的正立面**，无明显透视
- [ ] 每个真实窗/门都有框，**无重复框**叠在同一开洞上
- [ ] 框贴**玻璃/门扇**，不是整圈窗框
- [ ] `window` = 0，`door` = 1（可用记事本打开 txt 抽查）
- [ ] 归一化值均在 **0–1**，且 `w`、`h` > 0
- [ ] 图片与 txt **stem 完全一致**
- [ ] val 集包含与 train **不同建筑**（避免同一张图的增强副本进 val）

**快速目视检查（可选）：**

用 Ultralytics 预览（需已安装 `ultralytics`）：

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').val(data='data/facade_yolo/facade.yaml', plots=True)"
```

若 custom 数据已合并进 `data/facade_yolo/`，训练脚本生成的 `runs/facade_yolo_v1/labels.jpg` 也可查看分布。

---

## 9. 训练与迭代

1. 将标注好的目录放在 `backend/data/facade_yolo_custom/`
2. 训练（会自动合并 custom 数据）：

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python scripts\train_yolo_facade.py --epochs 80
```

3. 验证：

```powershell
.\.venv\Scripts\python scripts\validate_yolo_facade.py
```

4. 重启 backend，在 Workspace 用 **真实 rectified 照片** 再跑 **Detect → Overlay 审查**

**建议迭代规模：**

| 阶段 | 真实标注张数 | 目标 |
|------|-------------|------|
| 第一轮 | 10–20 张 | 覆盖常见窗格 + 单门布局 |
| 第二轮 | +20 张 | 补充失败案例（暗光、遮挡、异形窗） |
| 第三轮 | +30 张 | 多材质立面、玻璃幕墙、无门立面 |

合成数据（训练脚本自动生成）只能保证流程跑通；**真实精度取决于 custom 标注质量**。

---

## 10. 常见问题

**Q：Workspace 能直接导出 YOLO 吗？**  
A：可以。**Export YOLO Labels** 会把当前 Overlay 框 + rectified 图写入 `facade_yolo_custom/{train|val}/`。见第 6 节。

**Q：能否直接标原始照片？**  
A：不建议。检测管线假设输入接近正立面；请先 Workspace **Rectify**。

**Q：一扇窗要标一个框还是整排一个框？**  
A：**每个开洞一个框**。一排四窗 = 四个 `window` 框。

**Q：门宽填 0 时 Overlay 没有门框？**  
A：正常。仅用于 IR 生成；标注时请在 LabelImg 里单独画 `door` 框。

**Q：LabelImg 生成的 class id 不对？**  
A：检查 `predefined_classes.txt` 第一行必须是 `window`，第二行 `door`。

**Q：训练后真实照片仍漏检？**  
A：把漏检/误检案例加入 val，标好后重训；优先增加**与失败场景相似**的图片，而非盲目堆数量。

---

## 11. 最小示例（可复制）

`building_001.txt`（800×600 正立面，左下门 + 上方四窗）：

```text
0 0.1750 0.3833 0.1500 0.3000
0 0.3750 0.3833 0.1500 0.3000
0 0.5750 0.3833 0.1500 0.3000
0 0.7750 0.3833 0.1500 0.3000
1 0.0500 0.7417 0.0750 0.3833
```

放入 `train/labels/` 后，对应 `train/images/building_001.jpg` 即可开始第一轮 fine-tune。
