# 水印检测标注平台

一个用于水印检测数据集标注的快速标注平台。

## 功能特性

- 📁 数据类型管理（前端可配置）
- 🖼️ 多格式图片支持 (jpg, png, webp, bmp, gif, tiff)
- ⚡ 图片预加载优化
- 🔄 撤销/重做/跳过操作
- ⌨️ 快捷键支持
- 📊 进度追踪
- 💾 JSONL 格式输出
- 📥 预标注导入

## 快速开始

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 启动服务

```bash
cd backend
python main.py
```

然后在浏览器中打开 http://localhost:8000

## 快捷键

| 快捷键 | 操作 |
|--------|------|
| `1` 或 `W` | 标记有水印 |
| `2` 或 `N` | 标记无水印 |
| `S` | 跳过 |
| `A` 或 `←` | 上一张 |
| `D` 或 `→` | 下一张 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+Y` | 重做 |
| `Ctrl+S` | 保存 |

## 输出格式

```jsonl
{"image_path": "/path/to/image.jpg", "label": 1, "dataset_type": "产品图", "timestamp": "2025-12-23T16:00:00"}
```
