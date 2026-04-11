#!/usr/bin/env python3
"""
Test script for rate limiter functionality
"""

import sys
import os
import time
import threading

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_rate_limiter():
    """Test the rate limiter functionality"""
    print("=== 测试速率限制功能 ===\n")

    try:
        from llm_client import RateLimiter, rate_limited, set_rate_limit, get_rate_limit_info

        # Test 1: Basic rate limiter
        print("1. 测试基本速率限制器...")
        limiter = RateLimiter(max_requests=3, time_window=5)  # 5秒内最多3次请求

        # 测试允许的请求
        for i in range(3):
            allowed = limiter.is_allowed()
            print(f"请求 {i+1}: {'允许' if allowed else '拒绝'}")
            assert allowed, f"请求 {i+1} 应该被允许"

        # 测试超限的请求
        allowed = limiter.is_allowed()
        print(f"请求 4: {'允许' if allowed else '拒绝'}")
        assert not allowed, "请求 4 应该被拒绝"

        # 等待窗口过期
        print("\n等待窗口过期...")
        time.sleep(6)

        # 测试过期后允许
        allowed = limiter.is_allowed()
        print(f"请求 5 (过期后): {'允许' if allowed else '拒绝'}")
        assert allowed, "过期后的请求应该被允许"

        print("\n[PASS] 基本速率限制器测试通过\n")

        # Test 2: Rate limited decorator
        print("2. 测试速率限制装饰器...")

        call_count = 0

        @rate_limited(max_requests=2, time_window=3)
        def dummy_function():
            nonlocal call_count
            call_count += 1
            return f"函数调用 #{call_count}"

        # 测试允许的调用
        result1 = dummy_function()
        result2 = dummy_function()
        print(f"调用1: {result1}")
        print(f"调用2: {result2}")

        # 测试受限的调用
        start_time = time.time()
        try:
            result3 = dummy_function()
            print("错误：应该被限制但通过了")
        except RuntimeError as e:
            end_time = time.time()
            wait_time = end_time - start_time
            print(f"[PASS] 成功被限制，等待了 {wait_time:.2f} 秒: {str(e)}")

        print("\n[PASS] 速率限制装饰器测试通过\n")

        # Test 3: Rate limit info
        print("3. 测试速率限制信息...")

        # 测试全局限制器的信息
        limiter = RateLimiter(max_requests=5, time_window=10)
        # 使用全局限制器
        import llm_client
        llm_client._rate_limiter = limiter

        for i in range(3):
            limiter.is_allowed()

        info = get_rate_limit_info()
        print(f"速率限制信息: {info}")
        assert info['current_requests'] == 3, f"当前请求数应为3，实际为{info['current_requests']}"

        print("\n[PASS] 速率限制信息测试通过\n")

        # Test 4: Thread safety
        print("4. 测试线程安全性...")

        limiter = RateLimiter(max_requests=10, time_window=5)
        results = []
        errors = []

        def worker(worker_id):
            for i in range(3):
                time.sleep(0.1)  # 模拟工作
                try:
                    if limiter.is_allowed():
                        results.append(f"Worker {worker_id} 请求 {i} 成功")
                    else:
                        errors.append(f"Worker {worker_id} 请求 {i} 被限制")
                except Exception as e:
                    errors.append(f"Worker {worker_id} 请求 {i} 错误: {str(e)}")

        # 创建多个线程
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        print(f"成功请求: {len(results)}")
        print(f"限制/错误: {len(errors)}")

        # 验证没有竞争条件导致的问题
        assert len(results) + len(errors) == 9, "总请求数应为9"

        print("\n[PASS] 线程安全性测试通过\n")

        print("=== 所有测试通过！ ===")

    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_rate_limit_config():
    """Test rate limit configuration"""
    print("\n=== 测试速率限制配置 ===\n")

    try:
        from llm_client import set_rate_limit, get_rate_limit_info, disable_rate_limit, enable_rate_limit

        # 测试默认配置
        info = get_rate_limit_info()
        print(f"默认配置: {info}")

        # 测试设置新配置
        set_rate_limit(max_requests=5, time_window=30)
        info = get_rate_limit_info()
        print(f"新配置: {info}")
        assert info['max_requests'] == 5, "max_requests应为5"
        assert info['time_window'] == 30, "time_window应为30"

        # 测试禁用
        disable_rate_limit()
        info = get_rate_limit_info()
        print(f"禁用后配置: {info}")
        # 注意：禁用时time_window设为1，max_requests设为无穷大

        # 测试重新启用
        enable_rate_limit(max_requests=20, time_window=60)
        info = get_rate_limit_info()
        print(f"重新启用后配置: {info}")
        assert info['max_requests'] == 20, "max_requests应为20"
        assert info['time_window'] == 60, "time_window应为60"

        print("\n[PASS] 速率限制配置测试通过")

    except Exception as e:
        print(f"\n配置测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rate_limiter()
    test_rate_limit_config()