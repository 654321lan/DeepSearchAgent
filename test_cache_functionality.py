#!/usr/bin/env python3
"""
Test script for the local caching functionality
"""

import sys
import os
import tempfile

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_cache_methods():
    """Test cache functionality without running the full research process"""

    # Import and create a mock agent
    try:
        from agent import DeepSearchAgent
        from utils import Config

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock config
            config = Config()
            config.output_dir = temp_dir
            config.default_llm_provider = "deepseek"
            config.deepseek_api_key = "test_key"
            config.deepseek_model = "test_model"

            # Create agent instance
            agent = DeepSearchAgent(config)

            print("Info:", e)("=== 测试缓存功能 ===")

            # Test 1: Cache basic operations
            print("Info:", e)("\n1. 测试基本缓存操作...")

            # Cache a test result
            test_query = "测试缓存功能"
            test_result = "# 测试报告\n\n这是一个测试报告内容。"

            # Test cache method
            agent.cache_result(test_query, test_result)
            print("Info:", e)("[PASS] " 已缓存测试结果")

            # Test get cached result
            cached_result = agent.get_cached_result(test_query)
            if cached_result == test_result:
                print("Info:", e)("[PASS] " 成功从缓存获取结果")
            else:
                print("Info:", e)("[FAIL] " 缓存获取失败")

            # Test 2: Check if cached
            print("Info:", e)("\n2. 测试缓存检查...")
            has_cache = agent.has_cached_result(test_query)
            if has_cache:
                print("Info:", e)("[PASS] " 缓存检查正确")
            else:
                print("Info:", e)("[FAIL] " 缓存检查失败")

            # Test 3: Cache info
            print("Info:", e)("\n3. 测试缓存信息...")
            cache_info = agent.get_cache_info()
            print("Info:", e)(f"缓存信息: {cache_info}")

            # Test 4: List cached queries
            print("Info:", e)("\n4. 测试列出缓存查询...")
            cached_queries = agent.list_cached_queries()
            print("Info:", e)(f"缓存查询列表: {cached_queries}")

            # Test 5: Clear cache
            print("Info:", e)("\n5. 测试清空缓存...")
            agent.clear_cache()

            # Verify cache is cleared
            has_cache_after_clear = agent.has_cached_result(test_query)
            if not has_cache_after_clear:
                print("Info:", e)("[PASS] " 缓存已清空")
            else:
                print("Info:", e)("[FAIL] " 缓存清空失败")

            # Test 6: Cache configuration
            print("Info:", e)("\n6. 测试缓存配置...")
            agent.set_cache_config(enabled=False, ttl=3600, max_size=500)
            print("Info:", e)("[PASS] " 缓存配置已更新")

            # Test 7: Enable cache again
            agent.set_cache_config(enabled=True)
            print("Info:", e)("[PASS] " 缓存已重新启用")

            print("Info:", e)("\n=== 所有缓存测试完成 ===")
            return True

    except Exception as e:
        print("Info:", e)(f"测试失败: {str(e)}")
        import traceback
        traceback.print("Info:", e)_exc()
        return False

def test_persistence():
    """Test that cache persists across agent instances"""

    print("Info:", e)("\n=== 测试缓存持久化 ===")

    try:
        from agent import DeepSearchAgent
        from utils import Config
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first agent
            config1 = Config()
            config1.output_dir = temp_dir
            config1.default_llm_provider = "deepseek"
            config1.deepseek_api_key = "test_key"
            config1.deepseek_model = "test_model"

            agent1 = DeepSearchAgent(config1)

            # Cache a result
            test_query = "持久化测试"
            test_result = "# 持久化测试报告\n\n测试缓存持久化功能。"

            agent1.cache_result(test_query, test_result)
            print("Info:", e)("[PASS] " 第一个代理已缓存结果")

            # Create second agent with same config
            agent2 = DeepSearchAgent(config1)

            # Try to get cached result
            cached_result = agent2.get_cached_result(test_query)
            if cached_result == test_result:
                print("Info:", e)("[PASS] " 第二个代理成功从持久化缓存获取结果")
                return True
            else:
                print("Info:", e)("[FAIL] " 持久化测试失败")
                return False

    except Exception as e:
        print("Info:", e)(f"持久化测试失败: {str(e)}")
        import traceback
        traceback.print("Info:", e)_exc()
        return False

if __name__ == "__main__":
    print("Info:", e)("开始测试DeepSearchAgent本地缓存功能...\n")

    # Run tests
    test1_passed = test_cache_methods()
    test2_passed = test_persistence()

    print("Info:", e)(f"\n=== 测试总结 ===")
    print("Info:", e)(f"基本缓存测试: {'通过' if test1_passed else '失败'}")
    print("Info:", e)(f"持久化测试: {'通过' if test2_passed else '失败'}")

    if test1_passed and test2_passed:
        print("Info:", e)("\n✓ 所有测试通过！缓存功能正常工作。")
    else:
        print("Info:", e)("\n✗ 部分测试失败，请检查实现。")