import os
import subprocess
import time
import requests
import signal

# 主播信息和平台配置
ANCHOR_NAME = "Chzzk"
LIVE_URL = "UPLink"  # 替换为主播的实际直播间 URL
CHECK_INTERVAL = 30  # 检测间隔时间（秒）
OUTPUT_DIR = "./recordings"  # 录制文件保存路径
PROXY = "http://127.0.0.1:7890"  # 本地代理地址

# 配置代理
proxies = {
    "http": PROXY,
    "https": PROXY
}

def is_live():
    """
    检测主播是否在直播
    通过页面检查或API接口获取直播状态。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
    }
    try:
        response = requests.get(LIVE_URL, headers=headers, proxies=proxies)
        response.raise_for_status()
        # 根据实际页面结构调整，例：判断页面中是否包含 "live"
        if "live" in response.text:
            return True
    except Exception as e:
        print(f"检测直播状态时出错: {e}")
    return False

def get_stream_url():
    """
    获取直播流地址
    """
    try:
        # 如果能够通过 streamlink 获取流地址，可以继续使用 streamlink
        command = ["streamlink", LIVE_URL, "best", "--http-proxy", PROXY]
        stream_url = subprocess.check_output(command, stderr=subprocess.PIPE).decode('utf-8').strip()
        return stream_url
    except subprocess.CalledProcessError:
        print("streamlink 获取流地址失败，尝试手动设置流 URL")
        # 手动设置流 URL
        return "streamlink"

def record_stream():
    """
    使用 ffmpeg 录制直播流，支持通过代理录制。
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file_flv = os.path.join(OUTPUT_DIR, f"{ANCHOR_NAME}_{timestamp}.flv")
    output_file_mp4 = os.path.join(OUTPUT_DIR, f"{ANCHOR_NAME}_{timestamp}.mp4")
    
    stream_url = get_stream_url()
    if not stream_url:
        print("无法获取流地址，录制失败")
        return
    
    try:
        # 使用 flv 格式录制，并设置更高的质量和码率
        command_record = [
            "ffmpeg",
            "-http_proxy", PROXY,  # 配置代理
            "-i", stream_url,  # 输入直播流地址
            "-c:v", "libx264",  # 强制使用 h264 编码器
            "-crf", "0",  # 无损压缩（最高质量）
            "-preset", "veryslow",  # 最慢编码，最优质量
            "-b:v", "50000k",  # 设置视频码率为 50 Mbps（尽可能高）
            "-f", "flv",  # 设置输出格式为 flv
            "-y",  # 覆盖输出文件
            output_file_flv
        ]
        print(f"开始录制直播流，保存到 {output_file_flv}")

        # 使用 subprocess.Popen 来启动录制并允许捕获中断信号
        process = subprocess.Popen(command_record, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 等待用户按下Ctrl+C来中断录制
        try:
            process.communicate(timeout=None)  # 永久等待直到用户手动中断
        except KeyboardInterrupt:
            print("录制中断，开始转换为 MP4 格式...")

        # 录制完成后转换为 mp4 格式
        print(f"正在转换为 MP4 格式，保存到 {output_file_mp4}")
        command_convert = [
            "ffmpeg",
            "-i", output_file_flv,  # 输入 flv 文件
            "-c:v", "libx264",  # 使用 h264 编码
            "-c:a", "aac",  # 使用 aac 音频编码
            "-crf", "0",  # 保持无损压缩
            "-preset", "veryslow",  # 使用最慢编码模式以确保质量
            "-b:v", "50000k",  # 高码率
            "-b:a", "320k",  # 高音频码率
            "-y",  # 覆盖输出文件
            output_file_mp4
        ]
        subprocess.run(command_convert, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # 删除 flv 文件，只保留 mp4
        os.remove(output_file_flv)
        print(f"录制和转换完成，文件保存在 {output_file_mp4}")

    except KeyboardInterrupt:
        print("录制中断，开始转换 MP4...")
    except Exception as e:
        print(f"录制失败: {e}")

def main():
    print(f"正在检测主播 {ANCHOR_NAME} 的直播状态...")
    while True:
        if is_live():
            print(f"{ANCHOR_NAME} 开始直播，开始录制...")
            record_stream()
            print(f"{ANCHOR_NAME} 直播结束，录制完成")
        else:
            print(f"{ANCHOR_NAME} 当前未直播，{CHECK_INTERVAL}秒后重新检测...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
