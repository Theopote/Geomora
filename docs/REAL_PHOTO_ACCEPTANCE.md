# 真实照片验收流程（Stage A · Real Photo）

在合成数据验收通过之后，用**真实建筑照片**验证重建主路径是否可用。

相关文档：

| 文档 | 用途 |
|------|------|
| `docs/ROADMAP.md` | **唯一子系统成熟度与 Gate 进度源**（RC-* / RC-G1） |
| `docs/ACCEPTANCE.md` | 合成数据 + 功能清单 |
| `docs/YOLO_LABELING.md` | 标注与 Workspace 导出 |
| `docs/YOLO_TRAINING.md` | 重训 YOLO |
| `docs/MODEL_ARTIFACT_POLICY.md` | 模型/数据集不进 git |
| `docs/RECONSTRUCTION_STATUS.md` | 技术交付日志 |

---

## 0. 前置条件

```powershell
cd F:\development\Geomora\backend
.\start_server.bat
```

- [ ] `http://127.0.0.1:8765/health` 返回 OK
- [ ] 已安装最新 `dist\geomora.rbz`
- [ ] `backend\models\facade_yolo_v1.onnx` 存在（见 `docs/YOLO_TRAINING.md`）

---

## 1. 基线：合成数据必须通过

在真实照片之前，先确认管线未回归：

| 步骤 | 操作 | 通过标准 |
|------|------|----------|
| B1 | Load `examples/facade_perspective_synthetic.jpg` → Rectify | 正立面无明显透视 |
| B2 | Detect (Auto) | ≥3 窗 + ≥1 门（合成 rectified 场景） |
| B3 | Rationalize → Validate → Generate | 几何生成成功，Ctrl+Z 可撤销 |

CLI 快速检测（可选）：

```powershell
cd F:\development\Geomora\backend
python ..\examples\generate_rectified_fixture.py
.\.venv\Scripts\python scripts\validate_yolo_facade.py
.\.venv\Scripts\python scripts\accept_real_photos.py --images ..\examples --method auto --min-windows 3
```

---

## 2. 准备真实样本（A1 基准：20 张）

Stage A 使用 **20 张**真实建筑照片（不是 5 张），按类别与 split 组织：

| 类别 | 数量 |
|------|------|
| 普通住宅立面 | 5 |
| 办公建筑 | 3 |
| 老建筑 | 3 |
| 商业立面 | 3 |
| 被树遮挡 | 2 |
| 强透视 | 2 |
| 暗光/反光 | 2 |

| Split | 数量 | 规则 |
|-------|------|------|
| train | 10 | 可 Export YOLO Labels 并重训 |
| val | 5 | 仅用于 `accept_real_photos.py --split val` |
| **hold-out** | **5** | **绝不参与训练** — 最终 Gate 用 |

清单文件：`examples/real_photos/benchmark/manifest.json`

目录建议：

```text
examples/real_photos/
  benchmark/manifest.json   # 进 git（仅元数据）
  perspective/              # 原始照片（gitignore）
  rectified/              # 本地 rectified（gitignore，除合成 fixture）
backend/cache/            # 本地验收缓存（gitignore）
```

原始照片与 rectified 不进 git；见 `docs/MODEL_ARTIFACT_POLICY.md`。

---

## 3. SketchUp 人工验收（主流程）

对每张真实照片执行同一 checklist：

```text
Load Image（或 Load Video → 选帧）
→ Original：拖四角框住整面立面
→ Rectify Facade
→ Detect Elements（Detection: Auto）
→ Overlay：删误检 / Draw window 补漏检
→ 核对 Auto-estimate wall size
→ Rationalize → Validate → Generate
→ 目视：窗洞位置、门洞、整体比例是否合理
```

### 单张通过标准

| # | 检查项 | 通过 |
|---|--------|------|
| RP-1 | Rectify 后面砖/窗线大致水平 | ☐ |
| RP-2 | 检测到的窗数量与肉眼一致（±1 可 Overlay 修正） | ☐ |
| RP-3 | 门：有则检出或手画；无则 door width=0 | ☐ |
| RP-4 | Overlay 修正后 **Export YOLO Labels (train)** | ☐ |
| RP-5 | Generate 后立面比例可接受（不要求毫米级精度） | ☐ |

### 批次通过标准（RC-G1 E2E evidence；旧称 A3 Gate）

| 指标 | 最低要求 |
|------|----------|
| 样本数 | **20** 张（manifest 定义） |
| hold-out 成功率 | ≥ **4/5** 在 Overlay 轻微修正（~1 分钟）后可 Generate |
| val window recall | ≥ **0.80**（RC-G1 detection evidence；A1 基线 0.70） |
| train 标注 | ≥ **10** 张 Export 并重训 YOLO 一次 |
| 阻塞缺陷 | 无「Rectify 完全失败」且无法手调四角 |

### Reconstruction Quality Score（RQS）

**最终指标是 Photo → 可用 SketchUp 模型**，不是 YOLO IoU。每张图满分 100：

| 维度 | 分值 |
|------|------|
| Perspective Rectification | 15 |
| Opening Detection | 20 |
| Opening Placement | 15 |
| Scale | 10 |
| Pattern Rationalization | 10 |
| Geometry Validity | 15 |
| SketchUp Editability | 10 |
| Human Correction Cost | 5 |

A1 基线：在 SketchUp 人工验收时填写 RQS，写入 `cache/benchmark_a1_e2e.json` 的 `e2e.rqs` 字段。

失败分类（A2 只修这些）：

`missed_window` · `false_window` · `missed_door` · `false_door` · `bad_rectify` · `wrong_scale` · `wrong_pattern` · `invalid_geometry` · `generate_failed`

记录表（可复制）：

```text
| ID | Split | Rectify | 窗(检/真) | 门 | Overlay | Generate | RQS | 失败类 | 备注 |
|----|-------|---------|-----------|-----|---------|----------|-----|--------|------|
|    |       | OK/FAIL |           | Y/N | 无/轻/重 | OK/FAIL  | /100 |        |      |
```

---

## 4. CLI 批量验收（有标注时）

将 Overlay 导出的数据放入 `backend/data/facade_yolo_custom/val/`，运行：

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python scripts\accept_real_photos.py `
  --dataset data\facade_yolo_custom `
  --split val `
  --method auto `
  --report cache\real_photo_acceptance.json
```

### 默认数值门槛（IoU ≥ 0.5）

| 类别 | Precision | Recall |
|------|-----------|--------|
| window | ≥ 0.60 | ≥ 0.70 |
| door（有标注时） | ≥ 0.50 | ≥ 0.50 |

无 label 的目录（仅 smoke）：

```powershell
.\.venv\Scripts\python scripts\accept_real_photos.py `
  --images ..\examples\real_photos\rectified `
  --method auto `
  --min-windows 1
```

### 退出码

- `0` — 全部通过  
- `1` — 至少一张 FAIL（可用于 CI / 本地回归）

---

## 5. 失败分流

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| Rectify 扭曲 | 四角未框住完整立面 | 重拖四角；避免包含天空/地面过大区域 |
| 0 窗检出 | 未 Rectify / YOLO 未训真实数据 | 先 Rectify；Export 标注 → 重训 YOLO |
| 窗过多 | 纹理/空调被误检 | Overlay Delete；导出负样本重训 |
| 门误检 | 暗区或入口阴影 | Delete + door width=0 |
| 比例离谱 | 墙尺寸未估准 | 关闭 Auto-scale 手填；或修正 Overlay 后重 Detect |
| Generate 失败 | IR 校验 | 看 Workspace 错误；Rationalize 后再 Validate |

---

## 6. 迭代闭环（推荐）

```text
真实照片 SketchUp 验收 (§3)
    ↓ 失败案例
Overlay 修正 → Export YOLO Labels
    ↓
train_yolo_facade.py --epochs 80
    ↓
accept_real_photos.py --dataset ... --split val
    ↓
SketchUp 复测同一批照片
```

每轮优先增加**失败类型**的样本，而不是重复简单立面。

---

## 7. RC-G1 E2E 签字标准（旧称 A3 Reconstruction Gate）

满足以下全部条件，可认为 **真实照片 Stage A 验收通过**（见 `docs/ROADMAP.md`）：

1. 合成基线（§1）通过  
2. A1：20 张 manifest 照片完成检测基线 + SketchUp E2E 记录  
3. A2：仅按失败分类改进检测/Rectify/Scale/Rationalize  
4. hold-out **≥4/5** 轻度 Overlay 后可 Generate；单张修正 ~1 分钟  
5. train ≥10 张标注 Export 并重训 YOLO 一次  
6. `accept_real_photos.py --split val` window recall ≥ **0.80**  
7. `cache/benchmark_a1_e2e.json` 与 `cache/real_photo_acceptance.json` 已存档  

Constraint Solver 已属于 **RC-C Prototype**，可在 RC-G1 前并行开发，但必须
通过 solver on/off ablation，不能因“已接入生产链”而视为 Validated。多视角
Fuse 与证据驱动模型选择分别归入 RC-O/RC-S 和 RC-A 的后续验证范围。

---

## 8. 命令速查

```powershell
# 健康检查
curl http://127.0.0.1:8765/health

# A1 检测基线（自动）

```powershell
.\.venv\Scripts\python scripts\run_real_photo_benchmark.py
.\.venv\Scripts\python scripts\accept_real_photos.py --images cache\real_photo_desktop_rectified --method auto --report cache\benchmark_a1_detection.json
```

# A1 SketchUp 人工验收

```powershell
# 生成验收包（hold-out 优先排序 + overlay + CSV 模板）
.\.venv\Scripts\python scripts\export_a1_checklist.py
# 浏览器打开 cache\benchmark_a1\index.html

# SketchUp 跑完 20 张后，填写 cache\benchmark_a1\checklist_scores.csv，再导入：
.\.venv\Scripts\python scripts\import_a1_e2e_scores.py --csv cache\benchmark_a1\checklist_scores.csv
```

# 合成 YOLO 验证
.\.venv\Scripts\python scripts\validate_yolo_facade.py

# val 集指标（有标注后）
.\.venv\Scripts\python scripts\accept_real_photos.py --dataset data\facade_yolo_custom --split val --method auto

# 重训（仅用 train split，禁止 hold-out）
.\.venv\Scripts\python scripts\train_yolo_facade.py --epochs 80

# 打包插件
cd F:\development\Geomora
powershell -ExecutionPolicy Bypass -File .\build_rbz.ps1
```
