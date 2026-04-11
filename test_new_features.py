import unittest
from unittest.mock import Mock, patch, MagicMock
from src.agent import DeepSearchAgent
import json


class TestNewFeatures(unittest.TestCase):
    """测试新增功能"""

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

    def test_need_research(self):
        """测试_need_research方法"""
        # 测试分数小于0.7的情况
        self.assertTrue(self.agent._need_research(0.6))

        # 测试分数等于0.7的情况
        self.assertFalse(self.agent._need_research(0.7))

        # 测试分数大于0.7的情况
        self.assertFalse(self.agent._need_research(0.8))

    def test_integrate_results_sorting(self):
        """测试_integrate_results方法的排序功能"""
        # 测试数据 - 包含不同分数的任务
        task_results = [
            {
                "sub_task": {"content": "任务1", "priority": 1, "type": "搜索"},
                "search_results": [],
                "validation": {"score": 0.9, "conclusion": "相关"}
            },
            {
                "sub_task": {"content": "任务2", "priority": 2, "type": "分析"},
                "search_results": [],
                "validation": {"score": 0.6, "conclusion": "相关"}
            },
            {
                "sub_task": {"content": "任务3", "priority": 1, "type": "搜索"},
                "search_results": [],
                "validation": {"score": 0.8, "conclusion": "相关"}
            }
        ]

        # 调用方法
        result = self.agent._integrate_results(task_results)

        # 验证结果
        self.assertEqual(len(result["tasks"]), 3)

        # 验证任务按分数从高到低排序
        # 应该是：任务1(0.9) -> 任务3(0.8) -> 任务2(0.6)
        self.assertEqual(result["tasks"][0]["content"], "任务1")
        self.assertEqual(result["tasks"][0]["score"], 0.9)

        self.assertEqual(result["tasks"][1]["content"], "任务3")
        self.assertEqual(result["tasks"][1]["score"], 0.8)

        self.assertEqual(result["tasks"][2]["content"], "任务2")
        self.assertEqual(result["tasks"][2]["score"], 0.6)

        # 验证总览包含正确的平均分数
        self.assertEqual(result["overview"], "共整合3个子任务，平均验证分数0.77")


if __name__ == '__main__':
    unittest.main()