#!/usr/bin/env python3
"""
Demonstration of DeepSearchAgent caching functionality
"""

import sys
import os
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def demo_cache_usage():
    """Demonstrate how the caching works"""

    try:
        from agent import DeepSearchAgent
        from utils import Config

        # Create a mock config for demonstration
        config = Config()
        config.output_dir = "demo_output"
        config.default_llm_provider = "deepseek"
        config.deepseek_api_key = "demo_key"  # This won't be used for cached results
        config.deepseek_model = "demo_model"

        # Create agent
        agent = DeepSearchAgent(config)

        print("=== DeepSearchAgent 缓存功能演示 ===\n")

        # Simulate a research that would be slow (but we'll cache it)
        demo_query = "什么是人工智能"

        print(f"查询: {demo_query}")
        print("\n首次执行（会执行完整的研究流程）:")
        print("-" * 50)

        # This would normally make API calls, but for demo we'll simulate
        # Let's manually cache a result to show how it works
        simulated_result = f"""# 关于人工智能的研究报告

## 人工智能概述
人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。

## 主要应用领域
1. **机器学习**：使计算机能够从数据中学习
2. **自然语言处理**：理解和生成人类语言
3. **计算机视觉**：让计算机"看见"和理解图像
4. **机器人技术**：创造能够与物理世界交互的机器

## 未来展望
人工智能技术将继续发展，预计将在医疗、教育、交通等领域带来革命性的变化。
"""

        # Cache the result
        agent.cache_result(demo_query, simulated_result)
        print("[模拟] 研究完成并已缓存")

        print("\n第二次执行相同查询（将使用缓存）:")
        print("-" * 50)

        # Now simulate getting from cache
        cached_result = agent.get_cached_result(demo_query)
        if cached_result:
            print("[缓存命中] 直接返回缓存结果，无需重新研究!")
            print(f"缓存结果长度: {len(cached_result)} 字符")

        # Show cache information
        print("\n缓存信息:")
        cache_info = agent.get_cache_info()
        for key, value in cache_info.items():
            print(f"  {key}: {value}")

        # List cached queries
        print("\n已缓存的查询:")
        cached_queries = agent.list_cached_queries()
        for i, query in enumerate(cached_queries, 1):
            print(f"  {i}. {query}")

        # Demonstrate cache configuration
        print("\n缓存配置演示:")
        print("禁用缓存...")
        agent.set_cache_config(enabled=False)

        # Try to cache with disabled cache
        agent.cache_result("测试禁用缓存", "这个结果不会被缓存")

        # Check cache size (should still be 1 since we disabled caching)
        cache_info_after = agent.get_cache_info()
        print(f"禁用缓存后的条目数: {cache_info_after['total_entries']}")

        print("\n重新启用缓存...")
        agent.set_cache_config(enabled=True)

        # Clear cache
        print("\n清空缓存...")
        agent.clear_cache()

        # Verify cache is empty
        final_cache_info = agent.get_cache_info()
        print(f"清空后的缓存条目数: {final_cache_info['total_entries']}")

        print("\n=== 演示完成 ===")
        print("\n缓存功能特点:")
        print("1. 使用pickle进行本地持久化存储")
        print("2. 相同查询直接返回缓存结果，不调用任何API")
        print("3. 支持TTL（缓存过期时间）和最大缓存大小限制")
        print("4. 提供丰富的缓存管理方法")
        print("5. 完全兼容原有代码结构")

    except Exception as e:
        print(f"演示失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_cache_usage()