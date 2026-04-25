# GRSAI CLI

GRSAI 图像生成命令行工具，基于 [GRSAI](https://grsai.com) API。

## 功能

- 支持 `gpt-image-2` 和 `nano-banana-pro` 两种模型
- 图片可选，支持纯文本生成或多张参考图
- 自动识别命令行参数（模型、图片、提示词、尺寸、比例、数量）
- 并行生成多张图片，失败自动重试
- 图片上传缓存（3天有效期，避免重复上传）

## 安装

```bash
pip install requests
```

## 使用

```bash
python grs.py [图片...] [提示词] [模型] [尺寸] [比例] [数量]
```

### 模型

**gpt-image-2**（默认）
- 比例: auto, 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 5:4, 4:5, 21:9, 9:21, 2:1, 1:2, 3:1, 1:3

**nano-banana-pro**
- 尺寸: 1K, 2K, 4K（默认 1K）
- 比例: auto, 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 5:4, 4:5, 21:9

### 示例

```bash
# gpt-image-2（默认）
python grs.py photo.png 做成3D模型
python grs.py photo.png 画成水彩风格 16:9 3x
python grs.py 画一只猫

# nano-banana-pro
python grs.py photo.png 变清晰 nano-banana-pro 2k 16:9

# 多张参考图
python grs.py a.png b.png 融合风格
```

### 其他参数

| 参数 | 说明 |
|------|------|
| 图片 | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` `.tiff` `.ico`，可选，支持多张 |
| 提示词 | 必填，非参数的文字自动作为提示词 |
| 数量 | `3x` 表示至少生成3张（默认 `1x`），按 Enter 可随时停止补发 |

## 配置

编辑 `grs.py` 顶部的配置：

```python
API_KEY = "your-api-key"  # 从 grsai.com 获取
API_BASE = "https://api.grsai.com"  # 海外节点
# API_BASE = "https://grsai.dakka.com.cn"  # 国内节点
```

## 输出文件名

自动生成格式：`图片名_提示词_月日_时分_序号.png`

例如：`photo_做成3D模型_0425_2150_1.png`

纯文本生成（无参考图）：`提示词_月日_时分_序号.png`

## 缓存

上传过的图片会缓存到 `cache.json`，3天内相同文件不会重复上传。

## License

MIT
