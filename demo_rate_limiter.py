#!/usr/bin/env python3
"""
Demonstration of rate limiter functionality
"""

import sys
import os
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def demo_rate_limiter():
    """Demonstrate rate limiter usage"""
    print("=== 速率限制器功能演示 ===\n")

    try:
        from llm_client import (
            RateLimiter,
            rate_limited,
            set_rate_limit,
            get_rate_limit_info,
            disable_rate_limit,
            enable_rate_limit
        )

        # 1. 基本使用
        print("1. 基本速率限制器使用示例")
        print("-" * 40)

        # 创建速率限制器：5秒内最多3次请求
        limiter = RateLimiter(max_requests=3, time_window=5)

        print("模拟请求（5秒内最多3次）:")
        for i in range(5):
            allowed = limiter.is_allowed()
            status = "[PASS] 通过" if allowed else "[FAIL] 被限制"
            print(f"  请求 {i+1}: {status}")

            if not allowed:
                # 获取需要等待的时间
                wait_time = limiter.get_wait_time()
                print(f"    需要等待: {wait_time:.2f} 秒")

        # 等待窗口过期
        print("\n等待5秒让窗口过期...")
        time.sleep(5)

        # 现在应该又可以请求了
        allowed = limiter.is_allowed()
        print(f"\n过期后请求: {'[PASS] 通过' if allowed else '[FAIL] 被限制'}")

        print("\n" + "="*50 + "\n")

        # 2. 装饰器使用
        print("2. 使用装饰器限制函数调用")
        print("-" * 40)

        call_count = 0

        @rate_limited(max_requests=2, time_window=3)
        def api_call():
            nonlocal call_count
            call_count += 1
            return f"API调用 #{call_count} - 时间: {time.strftime('%H:%M:%S')}"

        print("模拟API调用（3秒内最多2次）:")

        # 第一次调用
        result1 = api_call()
        print(f"  {result1}")

        # 第二次调用
        result2 = api_call()
        print(f"  {result2}")

        # 第三次调用会被限制
        print("  尝试第三次调用...")
        start_time = time.time()
        try:
            result3 = api_call()
            print("  错误：应该被限制")
        except RuntimeError as e:
            end_time = time.time()
            print(f"  [PASS] 正确被限制，耗时: {end_time - start_time:.2f}秒")
            print(f"  错误信息: {str(e)}")

        print("\n" + "="*50 + "\n")

        # 3. 全局配置
        print("3. 全局速率限制配置")
        print("-" * 40)

        # 设置默认速率限制
        print("设置默认速率限制：5次请求/10秒")
        set_rate_limit(max_requests=5, time_window=10)

        info = get_rate_limit_info()
        print(f"当前配置: {info}")

        # 更快的限制用于演示
        print("\n设置更严格的限制：2次请求/3秒")
        set_rate_limit(max_requests=2, time_window=3)
        info = get_rate_limit_info()
        print(f"新配置: {info}")

        print("\n" + "="*50 + "\n")

        # 4. 禁用和启用
        print("4. 禁用和启用速率限制")
        print("-" * 40)

        # 禁用速率限制
        print("禁用速率限制...")
        disable_rate_limit()
        info = get_rate_limit_info()
        print(f"禁用后: {info}")

        # 重新启用
        print("\n重新启用速率限制（10次请求/60秒）...")
        enable_rate_limit(max_requests=10, time_window=60)
        info = get_rate_limit_info()
        print(f"启用后: {info}")

        print("\n" + "="*50 + "\n")

        # 5. 实际应用场景
        print("5. 实际应用场景示例")
        print("-" * 40)

        @rate_limited(max_requests=5, time_window=60)  # 每分钟最多5次API调用
        def make_api_request(endpoint: str):
            return f"成功调用 {endpoint}"

        # 模拟多个API调用
        endpoints = ["users", "posts", "comments", "likes", "followers", "following"]

        print("模拟API调用（限制：每分钟5次）:")
        for endpoint in endpoints:
            try:
                result = make_api_request(endpoint)
                print(f"  [PASS] {result}")
            except RuntimeError as e:
                print(f"  [FAIL] {str(e)}")

        print("\n=== 演示完成 ===")
        print("\n速率限制器特点:")
        print("1. 固定时间窗口算法")
        print("2. 线程安全，支持多线程环境")
        print("3. 可配置的最大请求数和时间窗口")
        print("4. 支持动态调整和禁用")
        print("5. 提供详细的统计信息")

    except Exception as e:
        print(f"演示失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_rate_limiter()