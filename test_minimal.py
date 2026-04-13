import requests
import json
import os

# 尝试配置代理（如果需要）
proxies = {
    'http': os.getenv('HTTP_PROXY', ''),
    'https': os.getenv('HTTPS_PROXY', '')
}

# 尝试禁用 SSL 验证（仅用于测试，生产环境请谨慎使用）
url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
headers = {
    "Authorization": "Bearer YOUR_ACTUAL_API_KEY",  # 请替换为实际的 API 密钥
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
data = {
    "model": "glm-4-flash",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 10
}
try:
    print("尝试使用代理（如果设置了）:", proxies)
    print("API 密钥前几位:", headers["Authorization"][:10] + "...")
    print("请求 URL:", url)

    # 尝试禁用 SSL 验证来排除证书问题
    resp = requests.post(url, headers=headers, json=data, timeout=30, verify=False, proxies=proxies)

    # 正确解码 UTF-8 响应
    try:
        print("状态码:", resp.status_code)
        print("响应内容:", resp.json())  # 使用 json() 方法自动解码
    except Exception as json_err:
        print("JSON 解码失败，尝试直接显示文本:")
        print("响应文本:", resp.text)
        print("原始字节:", resp.content[:100])

except Exception as e:
    print("请求失败:", e)
    print("错误类型:", type(e).__name__)

    print("\n解决方案建议:")
    print("1. 请确保 API 密钥正确 - 认证失败 (401) 表示密钥不正确或缺失")
    print("2. 如果使用代理，请设置 HTTP_PROXY 和 HTTPS_PROXY 环境变量")
    print("3. 尝试更新 requests 库: pip install --upgrade requests")
    print("4. 检查网络连接是否正常")