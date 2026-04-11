#!/usr/bin/env python3
"""
阶段4功能最终验证脚本
测试新增功能是否正常工作，并验证异常处理
"""

import sys
import os
from unittest.mock import MagicMock
import time

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from src.agent import DeepSearchAgent


def test_exception_handling():
    """测试异常处理"""
    print("测试异常处理...")

    # 创建Agent实例
    mock_config = MagicMock()
    mock_config.default_llm_provider = "deepseek"
    mock_config.deepseek_api_key = "test_key"
    mock_config.deepseek_model = "deepseek-chat"
    mock_config.max_search_results = 5
    mock_config.search_timeout = 30
    mock_config.tavily_api_key = "test_tavily_key"
    mock_config.output_dir = "test_output"
    mock_config.max_reflections = 2
    mock_config.save_intermediate_states = False
    mock_config.max_content_length = 5000

    agent = DeepSearchAgent(mock_config)

    # 测试缓存异常处理
    try:
        # 正常缓存
        result = {"test": "data"}
        agent._cache_result("normal_key", result)
        assert agent._get_cached_result("normal_key") == result

        # 测试缓存异常处理（应该捕获异常但不崩溃）
        agent._cache_result(None, result)  # 这不应该抛出异常
        print("  [PASS] 缓存异常处理正常")

    except Exception as e:
        print(f"  [FAIL] 缓存异常处理失败: {e}")
        return False

    # 测试重试策略异常处理
    try:
        # 正常重试策略
        retry_strat = agent._api_retry(5, 1.0)
        assert len(retry_strat["retry_sequence"]) == 5

        # 测试边界值
        retry_strat = agent._api_retry(0, 1.0)
        assert len(retry_strat["retry_sequence"]) == 0

        # 测试负数重试次数
        retry_strat = agent._api_retry(-1, 1.0)
        assert len(retry_strat["retry_sequence"]) == 0

        print("  [PASS] 重试策略异常处理正常")

    except Exception as e:
        print(f"  [FAIL] 重试策略异常处理失败: {e}")
        return False

    # 测试任务迁移异常处理
    try:
        # 正常迁移
        agent.is_busy = True
        migration = agent._simulate_task_migration("agent_001")
        assert migration["is_migratable"] == True

        # 测试迁移到自身
        migration = agent._simulate_task_migration("current")
        assert migration["is_migratable"] == False

        # 测试None目标
        migration = agent._simulate_task_migration(None)
        assert migration["target_agent_id"] is None

        print("  [PASS] 任务迁移异常处理正常")

    except Exception as e:
        print(f"  [FAIL] 任务迁移异常处理失败: {e}")
        return False

    return True


def test_performance():
    """测试性能"""
    print("\n测试性能...")

    # 创建Agent实例
    mock_config = MagicMock()
    mock_config.default_llm_provider = "deepseek"
    mock_config.deepseek_api_key = "test_key"
    mock_config.deepseek_model = "deepseek-chat"
    mock_config.max_search_results = 5
    mock_config.search_timeout = 30
    mock_config.tavily_api_key = "test_tavily_key"
    mock_config.output_dir = "test_output"
    mock_config.max_reflections = 2
    mock_config.save_intermediate_states = False
    mock_config.max_content_length = 5000

    agent = DeepSearchAgent(mock_config)

    # 测试缓存性能
    start_time = time.time()
    for i in range(10000):
        agent._cache_result(f"key_{i}", {"data": f"value_{i}"})
    cache_time = time.time() - start_time

    start_time = time.time()
    for i in range(10000):
        agent._get_cached_result(f"key_{i}")
    read_time = time.time() - start_time

    print(f"  缓存写入10000条: {cache_time:.4f}秒")
    print(f"  缓存读取10000条: {read_time:.4f}秒")

    if cache_time < 1.0 and read_time < 1.0:
        print("  [PASS] 性能测试通过")
        return True
    else:
        print("  [FAIL] 性能测试不通过")
        return False


def test_edge_cases():
    """测试边界情况"""
    print("\n测试边界情况...")

    # 创建Agent实例
    mock_config = MagicMock()
    mock_config.default_llm_provider = "deepseek"
    mock_config.deepseek_api_key = "test_key"
    mock_config.deepseek_model = "deepseek-chat"
    mock_config.max_search_results = 5
    mock_config.search_timeout = 30
    mock_config.tavily_api_key = "test_tavily_key"
    mock_config.output_dir = "test_output"
    mock_config.max_reflections = 2
    mock_config.save_intermediate_states = False
    mock_config.max_content_length = 5000

    agent = DeepSearchAgent(mock_config)

    # 测试各种边界值
    test_cases = [
        ("空字符串", ""),
        ("特殊字符", "!@#$%^&*()"),
        ("Unicode", "测试中文字符 üñîçøde"),
        ("超长字符串", "x" * 10000),
        ("None值", None),
    ]

    for name, key in test_cases:
        try:
            # 测试缓存
            if key is not None:
                agent._cache_result(key, {"test": "value"})
                result = agent._get_cached_result(key)
                assert result is not None

            # 测试重试策略
            retry = agent._api_retry(10, 0.1)
            assert len(retry["retry_sequence"]) == 10

            # 测试迁移
            agent.is_busy = True
            migration = agent._simulate_task_migration(str(key))
            assert "target_agent_id" in migration

            print(f"  [PASS] {name}测试通过")

        except Exception as e:
            print(f"  [FAIL] {name}测试失败: {e}")
            return False

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("阶段4功能最终验证")
    print("=" * 60)

    all_passed = True

    # 测试异常处理
    if not test_exception_handling():
        all_passed = False

    # 测试性能
    if not test_performance():
        all_passed = False

    # 测试边界情况
    if not test_edge_cases():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("[PASS] 所有验证通过！阶段4功能完全正常。")
        return 0
    else:
        print("[FAIL] 部分验证失败，请检查代码。")
        return 1


if __name__ == "__main__":
    sys.exit(main())