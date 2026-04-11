import unittest
from unittest.mock import Mock, patch, MagicMock
from src.agent import DeepSearchAgent


class TestEvaluationFeatures(unittest.TestCase):
    """测试评估功能"""

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

    def test_evaluation_constants(self):
        """测试评估指标常量"""
        # 验证常量存在且值正确
        self.assertEqual(self.agent.QUALITY_SCORE, "质量分")
        self.assertEqual(self.agent.COMPLETENESS, "完整度")
        self.assertEqual(self.agent.ACCURACY, "准确率")

    def test_evaluate_task(self):
        """测试_evaluate_task方法"""
        # 测试不同输入情况
        # 测试1：所有指标都是1.0
        result1 = self.agent._evaluate_task(1.0, 1.0, 1.0)
        self.assertEqual(result1, 1.0)  # 1.0*0.5 + 1.0*0.3 + 1.0*0.2 = 1.0

        # 测试2：所有指标都是0.0
        result2 = self.agent._evaluate_task(0.0, 0.0, 0.0)
        self.assertEqual(result2, 0.0)  # 0.0*0.5 + 0.0*0.3 + 0.0*0.2 = 0.0

        # 测试3：混合指标
        result3 = self.agent._evaluate_task(0.8, 0.7, 0.9)
        expected = 0.8 * 0.5 + 0.7 * 0.3 + 0.9 * 0.2
        self.assertAlmostEqual(result3, expected, places=6)

        # 测试4：边界值
        result4 = self.agent._evaluate_task(1.2, 0.5, 0.3)  # 质量分超过1.0
        expected4 = 1.0 * 0.5 + 0.5 * 0.3 + 0.3 * 0.2
        self.assertEqual(result4, expected4)  # 应该被限制在0-1范围内

        # 测试5：边界值
        result5 = self.agent._evaluate_task(-0.1, 0.5, 0.3)  # 质量分小于0
        expected5 = 0.0 * 0.5 + 0.5 * 0.3 + 0.3 * 0.2
        self.assertEqual(result5, expected5)  # 应该被限制在0-1范围内

        # 测试6：典型情况
        result6 = self.agent._evaluate_task(0.7, 0.8, 0.6)
        expected6 = 0.7 * 0.5 + 0.8 * 0.3 + 0.6 * 0.2
        self.assertAlmostEqual(result6, expected6, places=6)


if __name__ == '__main__':
    unittest.main()