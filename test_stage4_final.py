#!/usr/bin/env python3
"""
测试阶段4新增功能的完整离线测试脚本
测试功能：搜索缓存、API重试、模拟任务迁移
"""

import unittest
import time
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# 导入所需模块
from src.agent import DeepSearchAgent


class TestStage4Features(unittest.TestCase):
    """阶段4功能测试类"""

    def setUp(self):
        """测试前的初始化"""
        # 创建模拟配置
        self.mock_config = MagicMock()
        self.mock_config.default_llm_provider = "deepseek"
        self.mock_config.deepseek_api_key = "test_key"
        self.mock_config.deepseek_model = "deepseek-chat"
        self.mock_config.max_search_results = 5
        self.mock_config.search_timeout = 30
        self.mock_config.tavily_api_key = "test_tavily_key"
        self.mock_config.output_dir = "test_output"
        self.mock_config.max_reflections = 2
        self.mock_config.save_intermediate_states = False
        self.mock_config.max_content_length = 5000

        # 创建Agent实例
        self.agent = DeepSearchAgent(self.mock_config)

        # 准备测试数据
        self.test_query = "分析2024年新能源汽车市场"
        self.cached_result = {
            "query": "test query",
            "results": [{"title": "Test Result", "content": "Test content"}],
            "timestamp": datetime.now().isoformat(),
            "score": 0.85
        }

    def tearDown(self):
        """测试后的清理"""
        # 清理测试文件
        test_files = ["test_output"]
        for file_path in test_files:
            if os.path.exists(file_path):
                import shutil
                shutil.rmtree(file_path)

    # ========== 搜索缓存功能测试 ==========

    def test_cache_initialization(self):
        """测试搜索缓存初始化"""
        self.assertIsInstance(self.agent.search_cache, dict)
        self.assertEqual(len(self.agent.search_cache), 0)

    def test_cache_and_retrieve_result(self):
        """测试缓存存储和获取"""
        # 缓存结果
        self.agent._cache_result(self.test_query, self.cached_result)

        # 验证缓存中存在
        self.assertIn(self.test_query, self.agent.search_cache)

        # 获取缓存结果
        retrieved_result = self.agent._get_cached_result(self.test_query)
        self.assertEqual(retrieved_result, self.cached_result)

    def test_cache_miss(self):
        """测试缓存未命中"""
        non_existent_query = "不存在的查询"
        result = self.agent._get_cached_result(non_existent_query)
        self.assertIsNone(result)

    def test_cache_overwrite(self):
        """测试缓存覆盖"""
        # 第一次缓存
        first_result = {"score": 0.8, "data": "first"}
        self.agent._cache_result(self.test_query, first_result)

        # 验证第一次结果
        self.assertEqual(self.agent.search_cache[self.test_query], first_result)

        # 第二次缓存（覆盖）
        second_result = {"score": 0.9, "data": "second"}
        self.agent._cache_result(self.test_query, second_result)

        # 验证覆盖结果
        self.assertEqual(self.agent.search_cache[self.test_query], second_result)

    def test_cache_with_special_characters(self):
        """测试包含特殊字符的查询缓存"""
        special_query = "查询@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`"
        self.agent._cache_result(special_query, self.cached_result)

        result = self.agent._get_cached_result(special_query)
        self.assertEqual(result, self.cached_result)

    def test_cache_with_empty_string(self):
        """测试空字符串查询缓存"""
        empty_query = ""
        self.agent._cache_result(empty_query, self.cached_result)

        result = self.agent._get_cached_result(empty_query)
        self.assertEqual(result, self.cached_result)

    def test_cache_with_unicode(self):
        """测试Unicode字符查询缓存"""
        unicode_query = "测试中文查询 üñîçøde"
        self.agent._cache_result(unicode_query, self.cached_result)

        result = self.agent._get_cached_result(unicode_query)
        self.assertEqual(result, self.cached_result)

    # ========== API重试功能测试 ==========

    def test_api_retry_initialization(self):
        """测试API重试逻辑初始化"""
        max_retries = 3
        base_wait_time = 1.0

        retry_strategy = self.agent._api_retry(max_retries, base_wait_time)

        # 验证返回结构
        self.assertIn("max_retries", retry_strategy)
        self.assertIn("base_wait_time", retry_strategy)
        self.assertIn("retry_sequence", retry_strategy)

        # 验证参数
        self.assertEqual(retry_strategy["max_retries"], max_retries)
        self.assertEqual(retry_strategy["base_wait_time"], base_wait_time)
        self.assertEqual(len(retry_strategy["retry_sequence"]), max_retries)

    def test_retry_sequence_calculation(self):
        """测试重试序列计算"""
        max_retries = 5
        base_wait_time = 0.5

        retry_strategy = self.agent._api_retry(max_retries, base_wait_time)

        # 验证指数退避计算
        expected_wait_times = [0.5, 1.0, 2.0, 4.0, 8.0]  # base_wait_time * 2^i
        actual_wait_times = [step["wait_time"] for step in retry_strategy["retry_sequence"]]

        self.assertEqual(actual_wait_times, expected_wait_times)

        # 验证累积等待时间
        expected_total_waits = [0.5, 1.5, 3.5, 7.5, 15.5]  # 累积和
        actual_total_waits = [step["total_wait"] for step in retry_strategy["retry_sequence"]]

        self.assertEqual(actual_total_waits, expected_total_waits)

    def test_retry_sequence_edge_cases(self):
        """测试重试序列边界情况"""
        # 测试0次重试
        retry_strategy = self.agent._api_retry(0, 1.0)
        self.assertEqual(len(retry_strategy["retry_sequence"]), 0)

        # 测试1次重试
        retry_strategy = self.agent._api_retry(1, 1.0)
        self.assertEqual(len(retry_strategy["retry_sequence"]), 1)
        self.assertEqual(retry_strategy["retry_sequence"][0]["wait_time"], 1.0)

        # 测试负数重试次数（应被处理）
        retry_strategy = self.agent._api_retry(-1, 1.0)
        self.assertEqual(len(retry_strategy["retry_sequence"]), 0)

    def test_retry_with_zero_base_wait(self):
        """测试基础等待时间为0"""
        retry_strategy = self.agent._api_retry(3, 0.0)

        # 所有等待时间应为0
        for step in retry_strategy["retry_sequence"]:
            self.assertEqual(step["wait_time"], 0.0)
            self.assertEqual(step["total_wait"], 0.0)

    def test_retry_with_large_values(self):
        """测试大数值重试"""
        max_retries = 10
        base_wait_time = 100.0  # 100秒

        retry_strategy = self.agent._api_retry(max_retries, base_wait_time)

        # 验证最后一次的等待时间
        last_step = retry_strategy["retry_sequence"][-1]
        expected_last_wait = base_wait_time * (2 ** (max_retries - 1))
        self.assertEqual(last_step["wait_time"], expected_last_wait)

    # ========== 模拟任务迁移功能测试 ==========

    def test_task_migration_when_busy(self):
        """测试Agent忙碌时的任务迁移"""
        # 设置Agent为忙碌状态
        self.agent.is_busy = True

        # 测试迁移到不同的Agent
        target_agent = "agent_001"
        migration_result = self.agent._simulate_task_migration(target_agent)

        # 验证迁移决策
        self.assertTrue(migration_result["is_migratable"])
        self.assertEqual(migration_result["source_agent_id"], "current")
        self.assertEqual(migration_result["target_agent_id"], target_agent)
        self.assertEqual(migration_result["reason"], "当前Agent繁忙，负载过高")
        self.assertGreater(migration_result["estimated_gain"], 0.0)
        self.assertEqual(migration_result["estimated_cost"], 0.2)

        # 验证收益计算基于历史评分
        expected_gain = round(self.agent.history_score * 0.8, 2)
        self.assertEqual(migration_result["estimated_gain"], expected_gain)

    def test_task_migration_when_not_busy(self):
        """测试Agent空闲时不迁移"""
        # 确保Agent为空闲状态
        self.agent.is_busy = False

        target_agent = "agent_001"
        migration_result = self.agent._simulate_task_migration(target_agent)

        # 验证不迁移
        self.assertFalse(migration_result["is_migratable"])
        self.assertEqual(migration_result["reason"], "当前Agent空闲，无需迁移")
        self.assertEqual(migration_result["estimated_gain"], 0.0)
        self.assertEqual(migration_result["estimated_cost"], 0.0)

    def test_task_migration_to_self(self):
        """测试迁移到自身的处理"""
        # 设置Agent为忙碌状态
        self.agent.is_busy = True

        # 尝试迁移到当前Agent
        migration_result = self.agent._simulate_task_migration("current")

        # 验证不迁移
        self.assertFalse(migration_result["is_migratable"])
        self.assertEqual(migration_result["reason"], "目标Agent是当前Agent，无需迁移")
        self.assertEqual(migration_result["estimated_gain"], 0.0)
        self.assertEqual(migration_result["estimated_cost"], 0.0)

    def test_task_migration_edge_cases(self):
        """测试任务迁移边界情况"""
        # 测试空的目标Agent ID
        self.agent.is_busy = True
        migration_result = self.agent._simulate_task_migration("")

        self.assertTrue(migration_result["is_migratable"])

        # 测试None的目标Agent ID
        migration_result = self.agent._simulate_task_migration(None)

        self.assertTrue(migration_result["is_migratable"])

        # 测试特殊字符的目标Agent ID
        special_id = "agent@#$%"
        migration_result = self.agent._simulate_task_migration(special_id)

        self.assertTrue(migration_result["is_migratable"])
        self.assertEqual(migration_result["target_agent_id"], special_id)

    def test_task_migration_with_high_history_score(self):
        """测试高历史评分时的迁移收益"""
        # 设置高历史评分
        self.agent.history_score = 0.95
        self.agent.is_busy = True

        migration_result = self.agent._simulate_task_migration("agent_001")

        # 验证收益计算
        expected_gain = round(0.95 * 0.8, 2)
        self.assertEqual(migration_result["estimated_gain"], expected_gain)

    def test_task_migration_with_zero_history_score(self):
        """测试零历史评分时的迁移收益"""
        # 设置零历史评分
        self.agent.history_score = 0.0
        self.agent.is_busy = True

        migration_result = self.agent._simulate_task_migration("agent_001")

        # 验证收益计算
        expected_gain = round(0.0 * 0.8, 2)
        self.assertEqual(migration_result["estimated_gain"], 0.0)

    def test_task_migration_with_negative_history_score(self):
        """测试负历史评分的处理（负值会产生负收益）"""
        # 设置负历史评分
        self.agent.history_score = -0.5
        self.agent.is_busy = True

        migration_result = self.agent._simulate_task_migration("agent_001")

        # 验证收益计算（负值会产生负收益）
        expected_gain = round(self.agent.history_score * 0.8, 2)
        self.assertEqual(migration_result["estimated_gain"], expected_gain)

    # ========== 集成测试 ==========

    def test_features_integration(self):
        """测试多个功能的集成使用"""
        # 1. 缓存搜索结果
        self.agent._cache_result("test_integration", self.cached_result)

        # 2. 验证缓存检索
        cached = self.agent._get_cached_result("test_integration")
        self.assertIsNotNone(cached)

        # 3. 设置Agent状态
        self.agent.is_busy = True
        original_history_score = self.agent.history_score

        # 4. 模拟任务迁移
        migration_result = self.agent._simulate_task_migration("agent_002")

        # 5. 生成重试策略
        retry_strategy = self.agent._api_retry(3, 0.5)

        # 验证所有功能正常工作
        self.assertIsNotNone(cached)
        self.assertTrue(migration_result["is_migratable"])
        self.assertEqual(len(retry_strategy["retry_sequence"]), 3)
        self.assertEqual(self.agent.history_score, original_history_score)

    def test_concurrent_operations(self):
        """测试并发操作模拟"""
        # 模拟多个缓存操作
        queries = [f"query_{i}" for i in range(10)]
        for i, query in enumerate(queries):
            result = {"score": 0.5 + (i * 0.05), "data": f"data_{i}"}
            self.agent._cache_result(query, result)

        # 验证所有缓存
        for query in queries:
            result = self.agent._get_cached_result(query)
            self.assertIsNotNone(result)

        # 验证缓存数量
        self.assertEqual(len(self.agent.search_cache), 10)

    def test_memory_usage(self):
        """测试内存使用情况"""
        import sys

        # 记录初始内存使用
        initial_size = sys.getsizeof(self.agent.search_cache)

        # 添加大量缓存数据
        for i in range(100):
            large_data = {"data": "x" * 1000, "score": 0.5}
            self.agent._cache_result(f"large_query_{i}", large_data)

        # 记录最终内存使用
        final_size = sys.getsizeof(self.agent.search_cache)

        # 验证缓存正常工作
        self.assertEqual(len(self.agent.search_cache), 100)
        self.assertGreater(final_size, initial_size)


class TestStage4Performance(unittest.TestCase):
    """阶段4功能性能测试"""

    def setUp(self):
        """性能测试初始化"""
        # 创建模拟配置
        self.mock_config = MagicMock()
        self.mock_config.default_llm_provider = "deepseek"
        self.mock_config.deepseek_api_key = "test_key"
        self.mock_config.deepseek_model = "deepseek-chat"
        self.mock_config.max_search_results = 5
        self.mock_config.search_timeout = 30
        self.mock_config.tavily_api_key = "test_tavily_key"
        self.mock_config.output_dir = "test_output"
        self.mock_config.max_reflections = 2
        self.mock_config.save_intermediate_states = False
        self.mock_config.max_content_length = 5000

        self.agent = DeepSearchAgent(self.mock_config)
        self.test_data = {
            "query": "性能测试查询",
            "results": [{"title": f"Result {i}", "content": "x" * 100} for i in range(100)]
        }

    def test_cache_performance(self):
        """测试缓存性能"""
        # 测试大量缓存操作
        start_time = time.time()

        for i in range(1000):
            self.agent._cache_result(f"perf_query_{i}", self.test_data)

        cache_time = time.time() - start_time

        # 测试缓存读取性能
        start_time = time.time()

        for i in range(1000):
            self.agent._get_cached_result(f"perf_query_{i}")

        read_time = time.time() - start_time

        print("\n缓存性能:")
        print(f"  存储1000条数据: {cache_time:.4f}秒")
        print(f"  读取1000条数据: {read_time:.4f}秒")

        # 验证操作完成
        self.assertLess(cache_time, 1.0)  # 应在1秒内完成
        self.assertLess(read_time, 1.0)  # 应在1秒内完成

    def test_retry_strategy_performance(self):
        """测试重试策略生成性能"""
        start_time = time.time()

        # 生成大量重试策略
        for i in range(100):
            self.agent._api_retry(10, 0.1)

        elapsed_time = time.time() - start_time

        print("\n重试策略生成性能:")
        print(f"  生成100个重试策略（每次10次重试）: {elapsed_time:.4f}秒")

        # 验证性能
        self.assertLess(elapsed_time, 5.0)  # 应在5秒内完成


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始阶段4功能测试")
    print("=" * 60)

    # 创建测试套件
    test_suite = unittest.TestSuite()

    # 添加功能测试
    tests = unittest.TestLoader().loadTestsFromTestCase(TestStage4Features)
    test_suite.addTest(tests)

    # 添加性能测试
    tests = unittest.TestLoader().loadTestsFromTestCase(TestStage4Performance)
    test_suite.addTest(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    # 返回测试是否全部通过
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    # 运行测试
    success = run_all_tests()

    if success:
        print("\n[SUCCESS] 所有测试通过！阶段4功能正常工作。")
    else:
        print("\n[FAILED] 部分测试失败，请检查代码。")
        sys.exit(1)