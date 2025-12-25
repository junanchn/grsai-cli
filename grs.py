# -*- coding: utf-8 -*-
"""GRSAI 图像生成脚本"""

import os
import sys
import json
import time
import hashlib
import requests

#############################
# 配置
#############################

API_KEY = "your-api-key"
API_BASE = "https://api.grsai.com"

FORMATS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".ico")
SIZES = ("1K", "2K", "4K")
RATIOS = ("auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "21:9")

CACHE_FILE = "cache.json"
CACHE_TIME = 3 * 24 * 60 * 60  # 3天(秒)

#############################
# 显示帮助
#############################

if len(sys.argv) < 3:
    print(f"""GRSAI 图像生成脚本

用法: python grs.py [图片...] [提示词] [尺寸] [比例]

图片格式: {", ".join(FORMATS)}
尺寸: {", ".join(SIZES)} (默认 1K)
比例: {", ".join(RATIOS)} (默认 auto)

示例:
  python grs.py photo.png 变清晰
  python grs.py photo.png 变清晰 2K 16:9
  python grs.py a.png b.png 融合风格 4K""")
    sys.exit(0)

#############################
# 解析参数
#############################

input_images = []   # 输入的图片文件
prompt_words = []   # 提示词
size = "1K"         # 尺寸
ratio = "auto"      # 比例

for arg in sys.argv[1:]:
    if arg.lower().endswith(FORMATS):
        if os.path.isfile(arg):
            input_images.append(arg)
        else:
            print("错误: 文件不存在:", arg)
            sys.exit(1)
    elif arg in SIZES:
        size = arg
    elif arg in RATIOS:
        ratio = arg
    else:
        prompt_words.append(arg)

prompt = " ".join(prompt_words)

if not input_images:
    print("错误: 请提供至少一张图片")
    sys.exit(1)

if not prompt:
    print("错误: 请提供提示词")
    sys.exit(1)

#############################
# 生成输出文件名
#############################

time_str = time.strftime("%m%d_%H%M%S")
image_names = "_".join(os.path.splitext(os.path.basename(img))[0] for img in input_images)
prompt_str = prompt[:20]

if len(image_names) < 20:
    output_file = f"{image_names}_{prompt_str}_{time_str}.png"
else:
    output_file = f"{prompt_str}_{time_str}.png"

#############################
# 读取缓存
#############################

# 缓存格式: {"文件哈希": {"url": "上传后的URL", "time": 上传时间戳}}
cache = {}
if os.path.isfile(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)

#############################
# 上传图片
#############################

print("上传图片...")
uploaded_urls = []

for image_path in input_images:
    # 计算文件哈希
    with open(image_path, "rb") as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    
    # 检查缓存是否有效
    if file_hash in cache:
        cached = cache[file_hash]
        if time.time() - cached["time"] < CACHE_TIME:
            print(f"  {image_path} -> 使用缓存")
            uploaded_urls.append(cached["url"])
            continue
    
    # 上传
    print(f"  {image_path} -> 上传中...")
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{API_BASE}/client/resource/uploadFile",
            headers={"xtx": API_KEY},
            files={"file": f},
            timeout=120
        )
    
    result = response.json()
    if result.get("code") != 0:
        print("上传失败:", result.get("msg", "未知错误"))
        sys.exit(1)
    
    url = result["data"]["url"]
    uploaded_urls.append(url)
    cache[file_hash] = {"url": url, "time": time.time()}

# 保存缓存
with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(cache, f)

#############################
# 生成图像
#############################

print(f"""
生成图像...
  提示词: {prompt}
  尺寸: {size}
  比例: {ratio}
  输出: {output_file}
""")

response = requests.post(
    f"{API_BASE}/v1/draw/nano-banana",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "nano-banana-pro",
        "prompt": prompt,
        "urls": uploaded_urls,
        "imageSize": size,
        "aspectRatio": ratio
    },
    stream=True,
    timeout=300
)

if response.status_code != 200:
    print(f"请求失败: {response.status_code}")
    print(response.text)
    sys.exit(1)

# 读取进度
result_url = None

for line in response.iter_lines(decode_unicode=True):
    # 跳过空行
    if not line:
        continue
    
    # 去掉 "data: " 前缀
    if line.startswith("data: "):
        line = line[6:]
    
    # 解析JSON
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue
    
    # 显示进度
    progress = data.get("progress", 0)
    status = data.get("status", "")
    print(f"\r进度: {progress}%", end="", flush=True)
    
    # 生成成功
    if status == "succeeded":
        result_url = data["results"][0]["url"]
        break
    
    # 生成失败
    if status == "failed":
        print()
        print("生成失败:", data.get("error", "未知错误"))
        sys.exit(1)

#############################
# 保存结果
#############################

if result_url:
    print("\n下载结果...")
    
    response = requests.get(result_url, timeout=60)
    
    with open(output_file, "wb") as f:
        f.write(response.content)
    
    print("已保存:", output_file)
else:
    print("\n错误: 没有收到结果")
