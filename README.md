# GRSAI CLI

GRSAI 图像生成命令行工具，基于 [GRSAI](https://grsai.com) API。

## 功能

- 支持多张参考图输入
- 自动识别命令行参数（图片、提示词、尺寸、比例）
- 图片上传缓存（3天有效期，避免重复上传）
- 实时显示生成进度

## 安装

```bash
pip install requests
```

## 使用

```bash
python grs.py [图片...] [提示词] [尺寸] [比例]
```

### 参数说明

| 参数 | 说明 | 可选值 |
|------|------|--------|
| 图片 | 一张或多张参考图 | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` `.tiff` `.ico` |
| 尺寸 | 输出图片尺寸 | `1K` `2K` `4K`（默认 `1K`） |
| 比例 | 输出图片比例 | `auto` `1:1` `16:9` `9:16` `4:3` `3:4` `3:2` `2:3` `5:4` `4:5` `21:9`（默认 `auto`） |
| 提示词 | 其他所有内容 | 任意文字 |

### 示例

```bash
# 基础用法
python grs.py photo.png 变清晰

# 指定尺寸和比例
python grs.py photo.png 添加特效 2K 16:9

# 多张参考图
python grs.py a.png b.png 融合风格 4K
```

## 配置

编辑 `grs.py` 顶部的配置：

```python
API_KEY = "your-api-key"  # 从 grsai.com 获取
API_BASE = "https://api.grsai.com"  # 海外节点
# API_BASE = "https://grsai.dakka.com.cn"  # 国内节点
```

## 输出文件名

自动生成格式：`图片名_提示词_月日_时分秒.png`

例如：`photo_变清晰_1225_143025.png`

## 缓存

上传过的图片会缓存到 `cache.json`，3天内相同文件不会重复上传。

## License

MIT

