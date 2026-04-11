import unittest
from unittest.mock import Mock, patch, MagicMock
from src.agent import DeepSearchAgent


class TestCacheAndRetry(unittest.TestCase):
    """测试缓存和重试功能"""

    def setUp(self):
        """测试前准备"""
        # 创建模拟的配置
        self.mock_config = Mock()
        self.mock_config.default_llm_provider = "deepseek"
        self.mock_config.deepseek_api_key = "mock_key"
        self.mock_config.deepseek_model = "mock_model"
        self.mock_config.output_dir = "mock_output_dir"
        self.mock_config.max_search_results = 5
        self.mock_config.search_timeout = 30
        self.mock_config.tavily_api_key = "mock_tavily_key"
        self.mock_config.max_reflections = 2
        self.mock_config.max_content_length = 1000

        # 创建DeepSearchAgent实例
        self.agent = DeepSearchAgent(self.mock_config)
        self.agent.llm_client = Mock()
        self.agent.llm_client.generate_json = Mock()

    def test_search_cache_initialization(self):
        """测试搜索缓存初始化"""
        self.assertEqual(self.agent.search_cache, {})
        self.assertIsInstance(self.agent.search_cache, dict)

    def test_get_cached_result(self):
        """测试从缓存获取结果"""
        # 测试缓存为空的情况
        result = self.agent._get_cached_result("查询1")
        self.assertIsNone(result)

        # 测试缓存中有数据的情况
        test_result = {"status": "success", "data": "test data"}
        self.agent.search_cache["查询1"] = test_result

        cached_result = self.agent._get_cached_result("查询1")
        self.assertEqual(cached_result, test_result)

    def test_cache_result(self):
        """测试缓存结果"""
        test_result = {"status": "success", "data": "test data"}

        # 缓存结果
        self.agent._cache_result("查询1", test_result)

        # 验证缓存中存在
        self.assertIn("查询1", self.agent.search_cache)
        self.assertEqual(self.agent.search_cache["查询1"], test_result)

    def test_api_retry(self):
        """测试API重试逻辑"""
        # 测试参数
        max_retries = 3
        base_wait_time = 1.0

        # 调用方法
        retry_strategy = self.agent._api_retry(max_retries, base_wait_time)

        # 验证返回结果结构
        self.assertIn("max_retries", retry_strategy)
        self.assertIn("base_wait_time", retry_strategy)
        self.assertIn("retry_sequence", retry_strategy)

        # 验证重试序列
        self.assertEqual(len(retry_strategy["retry_sequence"]), max_retries)

        # 验证指数退避计算
        for i, attempt in enumerate(retry_strategy["retry_sequence"]):
            self.assertEqual(attempt["attempt"], i + 1)
            expected_wait = base_wait_time * (2 ** i)
            self.assertEqual(attempt["wait_time"], expected_wait)

    def test_api_retry_edge_cases(self):
        """测试API重试的边界情况"""
        # 测试0次重试
        result = self.agent._api_retry(0, 1.0)
        self.assertEqual(len(result["retry_sequence"]), 0)

        # 测试1次重试
        result = self.agent._api_retry(1, 2.0)
        self.assertEqual(len(result["retry_sequence"]), 1)
        self.assertEqual(result["retry_sequence"][0]["wait_time"], 2.0)

    def test_simulate_task_migration(self):
        """测试任务迁移模拟"""
        # 测试情况1：当前Agent忙碌
        self.agent.is_busy = True
        self.agent.history_score = 0.8

        result = self.agent._simulate_task_migration("agent_002")

        self.assertTrue(result["is_migratable"])
        self.assertEqual(result["reason"], "当前Agent繁忙，负载过高")
        self.assertEqual(result["estimated_gain"], 0.64)  # 0.8 * 0.8
        self.assertEqual(result["estimated_cost"], 0.2)

        # 测试情况2：当前Agent空闲
        self.agent.is_busy = False
        result = self.agent._simulate_task_migration("agent_002")

        self.assertFalse(result["is_migratable"])
        self.assertEqual(result["reason"], "当前Agent空闲，无需迁移")
        self.assertEqual(result["estimated_gain"], 0.0)
        self.assertEqual(result["estimated_cost"], 0.0)

        # 测试情况3：目标Agent是当前Agent
        self.agent.is_busy = True
        result = self.agent._simulate_task_migration("current")

        self.assertFalse(result["is_migratable"])
        self.assertEqual(result["reason"], "目标Agent是当前Agent，无需迁移")


if __name__ == '__main__':
    unittest.main()