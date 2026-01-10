# -*- coding: utf-8 -*-
"""
GRSAI 图像生成脚本

1. 命令行参数：图片文件(可多个)、提示词、尺寸(1K/2K/4K)、比例(16:9等)、数量(3x格式)
2. 上传图片到 API，使用 MD5 哈希缓存避免重复上传，缓存有效期3天
3. 调用流式 API 生成图像，解析 SSE 响应获取结果
4. 支持并行生成多张图片，失败自动重试直到达到目标数量，有并行上限
5. 补发策略可配置，按 Enter 可随时停止补发只等剩余任务完成
6. 输出文件名包含原图名、提示词、时间戳，自动序号避免覆盖
======================
"""

import os
import sys
import json
import time
import hashlib
import requests
import concurrent.futures
import threading
from threading import Lock, Event

#############################
# 配置
#############################

API_KEY = "这里替换你的 API Key"
API_BASE = "https://api.grsai.com"

FORMATS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".ico")
SIZES = ("1K", "2K", "4K")
RATIOS = ("auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "21:9")

CACHE_FILE = "cache.json"
CACHE_TIME = 3 * 24 * 60 * 60
MAX_PARALLEL = 10

#############################
# 帮助
#############################

def show_help():
    print(f"""GRSAI 图像生成脚本

用法: python grs.py [图片...] [提示词] [尺寸] [比例] [数量]

图片格式: {", ".join(FORMATS)}
尺寸: {", ".join(SIZES)} (默认 1K)
比例: {", ".join(RATIOS)} (默认 auto)
数量: 3x 表示至少生成3张 (默认 1x)

示例:
  python grs.py photo.png 变清晰
  python grs.py photo.png 变清晰 2k 16:9 3x
  python grs.py a.png b.png 融合风格 4K 5X""")
    sys.exit(0)

#############################
# 解析参数
#############################

def parse_args():
    if len(sys.argv) < 3:
        show_help()
    
    images = []
    words = []
    size = "1K"
    ratio = "auto"
    count = 1
    
    for arg in sys.argv[1:]:
        lower = arg.lower()
        upper = arg.upper()
        
        if lower.endswith(FORMATS):
            if not os.path.isfile(arg):
                sys.exit(f"错误: 文件不存在: {arg}")
            images.append(arg)
        elif upper in SIZES:
            size = upper
        elif arg in RATIOS:
            ratio = arg
        elif lower.endswith("x") and lower[:-1].isdigit():
            count = int(lower[:-1])
        else:
            words.append(arg)
    
    prompt = " ".join(words)
    if not prompt:
        sys.exit("错误: 请提供提示词")
    
    return images, prompt, size, ratio, count

#############################
# 上传图片
#############################

def upload_images(images):
    """上传图片，返回URL列表。使用缓存避免重复上传。"""
    # 加载缓存
    cache = {}
    if os.path.isfile(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
    
    urls = []
    for path in images:
        # 计算哈希
        with open(path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        # 检查缓存
        if file_hash in cache and time.time() - cache[file_hash]["time"] < CACHE_TIME:
            print(f"  {path} -> 缓存")
            urls.append(cache[file_hash]["url"])
            continue
        
        # 上传
        print(f"  {path} -> 上传中...")
        with open(path, "rb") as f:
            resp = requests.post(
                f"{API_BASE}/client/resource/uploadFile",
                headers={"xtx": API_KEY},
                files={"file": f},
                timeout=120
            )
        
        result = resp.json()
        if result.get("code") != 0:
            sys.exit(f"上传失败: {result.get('msg', '未知错误')}")
        
        url = result["data"]["url"]
        urls.append(url)
        cache[file_hash] = {"url": url, "time": time.time()}
    
    # 保存缓存
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    
    return urls

#############################
# 生成一张图片
#############################

def generate_one(urls, prompt, size, ratio):
    """
    生成一张图片。
    返回: (成功?, 文件路径或错误信息)
    """
    # 发送请求
    try:
        resp = requests.post(
            f"{API_BASE}/v1/draw/nano-banana",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nano-banana-pro",
                "prompt": prompt,
                "urls": urls,
                "imageSize": size,
                "aspectRatio": ratio
            },
            stream=True,
            timeout=300
        )
    except Exception as e:
        return False, f"请求异常: {e}"
    
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"
    
    # 读取流式响应
    result_url = None
    buffer = ""
    
    for chunk in resp.iter_content(chunk_size=1024):
        buffer += chunk.decode("utf-8", errors="ignore")
        
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            if line.startswith("data: "):
                line = line[6:]
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            status = data.get("status", "")
            if status == "succeeded":
                result_url = data["results"][0]["url"]
                break
            if status == "failed":
                reason = data.get("failure_reason", "")
                error = data.get("error", "")
                msg = error or reason or "生成失败"
                return False, msg
    
    if not result_url:
        return False, "未收到结果"
    
    # 下载图片
    try:
        img_resp = requests.get(result_url, timeout=60)
        return True, img_resp.content
    except Exception as e:
        return False, f"下载失败: {e}"

#############################
# 主流程
#############################

def main():
    # 解析参数
    images, prompt, size, ratio, target = parse_args()
    
    # 生成输出文件名模板
    time_str = time.strftime("%m%d_%H%M")
    names = "_".join(os.path.splitext(os.path.basename(p))[0] for p in images)
    prompt_short = prompt[:200]
    template = f"{names}_{prompt_short}_{time_str}" if len(names) < 40 else f"{prompt_short}_{time_str}"
    for c in '\\/:*?"<>|':
        template = template.replace(c, "_")
    
    # 上传图片
    print("上传图片...")
    urls = upload_images(images)
    
    # 开始生成
    print(f"\n生成图像...")
    print(f"  提示词: {prompt}")
    print(f"  尺寸: {size}, 比例: {ratio}")
    print(f"  目标: {target}张, 并行上限: {MAX_PARALLEL}\n")
    
    success = 0
    fail = 0
    counter = 0
    lock = Lock()
    stop = Event()
    
    # 监听 Enter 停止补发
    def listen():
        input()
        stop.set()
        print("\n⏸ 已停止补发，等待剩余任务...")
    threading.Thread(target=listen, daemon=True).start()
    print("(按 Enter 停止补发)\n")
    
    def task():
        """单个生成任务"""
        ok, result = generate_one(urls, prompt, size, ratio)
        
        if ok:
            # 保存文件
            with lock:
                nonlocal counter
                counter += 1
                path = f"{template}_{counter}.png"
            with open(path, "wb") as f:
                f.write(result)
            return True, path
        else:
            return False, result
    
    # 并行执行
    with concurrent.futures.ThreadPoolExecutor() as pool:
        futures = {pool.submit(task) for _ in range(target)}
        
        while futures:
            done, futures = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            for f in done:
                ok, result = f.result()
                
                # ===== 补发策略 =====
                if stop.is_set() or target - success <= 0:
                    relaunch = 0        # 停止或已达标
                elif ok:
                    relaunch = 0        # 成功后补发数量
                else:
                    relaunch = 1        # 失败后补发数量
                
                # 限制并行上限
                relaunch = min(relaunch, MAX_PARALLEL - len(futures))
                for _ in range(relaunch):
                    futures.add(pool.submit(task))
                
                # 输出状态
                running = len(futures)
                if ok:
                    success += 1
                    print(f"✓ 成功 {success}/{target}  {result}  (运行: {running})")
                else:
                    fail += 1
                    if relaunch:
                        print(f"✗ 失败#{fail}: {result}  (补发+{relaunch}, 运行: {running})")
                    else:
                        print(f"✗ 失败#{fail}: {result}  (不补发, 运行: {running})")
    
    print(f"\n完成! 成功: {success}, 失败: {fail}")

if __name__ == "__main__":
    main()
