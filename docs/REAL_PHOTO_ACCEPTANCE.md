# 真实照片验收流程（Stage A · Real Photo）

在合成数据验收通过之后，用**真实建筑照片**验证重建主路径是否可用。

相关文档：

| 文档 | 用途 |
|------|------|
| `docs/ACCEPTANCE.md` | 合成数据 + 功能清单 |
| `docs/YOLO_LABELING.md` | 标注与 Workspace 导出 |
| `docs/YOLO_TRAINING.md` | 重训 YOLO |
| `docs/RECONSTRUCTION_STATUS.md` | 总体进度 |

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

## 2. 准备真实样本

建议首批 **5–10 张**，覆盖不同场景：

| 类型 | 说明 |
|------|------|
| 标准行列窗 + 单门 | 最常见住宅立面 |
| 无门立面 | 验证 door 不误检 |
| 暗光 / 反光 | 检测鲁棒性 |
| 遮挡（树、车） | 允许 Overlay 手修 |
| 视频关键帧 | Load Video → 选帧 → 同上流程 |

目录建议：

```text
examples/real_photos/
  perspective/     # 原始照片（SketchUp 里 Load Image 用）
  rectified/       # 可选：已 Rectify 的图，供 CLI 批量检测
```

`perspective/` 不进 git 亦可；`rectified/` 可放脱敏样本供团队 CLI 验收。

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
| R1 | Rectify 后面砖/窗线大致水平 | ☐ |
| R2 | 检测到的窗数量与肉眼一致（±1 可 Overlay 修正） | ☐ |
| R3 | 门：有则检出或手画；无则 door width=0 | ☐ |
| R4 | Overlay 修正后 **Export YOLO Labels (train)** | ☐ |
| R5 | Generate 后立面比例可接受（不要求毫米级精度） | ☐ |

### 批次通过标准（Stage A）

| 指标 | 最低要求 |
|------|----------|
| 样本数 | ≥ **5** 张不同建筑/角度 |
| 成功率 | ≥ **4/5** 在 Overlay 轻微修正后可 Generate |
| 阻塞缺陷 | 无「Rectify 完全失败」且无法手调四角的情况 |

记录表（可复制）：

```text
| 文件名 | Rectify | 窗(检/真) | 门 | Overlay 修正 | Generate | 备注 |
|--------|---------|-----------|-----|--------------|----------|------|
|        | OK/FAIL |           | Y/N | 无/轻/重     | OK/FAIL  |      |
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

## 7. Stage A 签字标准

满足以下全部条件，可认为 **Phase 3 真实照片 Stage A 验收通过**：

1. 合成基线（§1）通过  
2. ≥5 张真实照片完成 §3 checklist，≥4/5 Generate 成功  
3. 至少 **10 张** train 标注已 Export 并重训 YOLO 一次  
4. `accept_real_photos.py --split val` 在 val 集上 window recall ≥ 0.70  
5. 验收记录表与 `cache/real_photo_acceptance.json` 已存档  

Stage B（后续）：多视角 Fuse、SAM 精修、毫米级尺度 — 不在本清单范围。

---

## 8. 命令速查

```powershell
# 健康检查
curl http://127.0.0.1:8765/health

# 合成 YOLO 验证
.\.venv\Scripts\python scripts\validate_yolo_facade.py

# val 集指标
.\.venv\Scripts\python scripts\accept_real_photos.py --dataset data\facade_yolo_custom --split val --method auto

# 重训
.\.venv\Scripts\python scripts\train_yolo_facade.py --epochs 80

# 打包插件
cd F:\development\Geomora
powershell -ExecutionPolicy Bypass -File .\build_rbz.ps1
```
