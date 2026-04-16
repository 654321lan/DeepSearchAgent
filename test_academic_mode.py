"""
测试学术模式和通用模式的全流程
"""

import os
import sys
import logging

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.utils.config import Config
from src.state.state import State
from src.agent import DeepSearchAgent

def test_config_validation():
    """测试配置验证逻辑"""
    logger.info("测试1: 配置验证逻辑")

    # 测试学术模式配置验证
    config_academic = Config(
        zhipu_api_key="test_key",
        academic_mode=True
    )
    assert config_academic.validate() == True, "学术模式配置验证失败"
    assert config_academic.default_llm_provider == "zhipu", "学术模式未强制设置为zhipu"
    logger.info("✅ 学术模式配置验证通过")

    # 测试非学术模式配置验证
    config_normal = Config(
        deepseek_api_key="test_deepseek_key",
        tavily_api_key="test_tavily",
        default_llm_provider="deepseek",
        academic_mode=False
    )
    assert config_normal.validate() == True, "非学术模式配置验证失败"
    logger.info("✅ 非学术模式配置验证通过")

    # 测试缺少Tavily API Key的非学术模式
    config_missing_tavily = Config(
        deepseek_api_key="test_deepseek_key",
        default_llm_provider="deepseek",
        academic_mode=False
    )
    assert config_missing_tavily.validate() == False, "缺少Tavily API Key应该验证失败"
    logger.info("✅ 缺少Tavily API Key的配置验证正确拒绝")

def test_state_persistence():
    """测试状态持久化功能"""
    logger.info("测试2: 状态持久化功能")

    # 创建状态并添加学术论文
    state = State(
        query="测试查询",
        report_title="测试报告"
    )

    # 添加学术论文
    state.academic_papers = [
        {
            "title": "测试论文1",
            "authors": ["作者1", "作者2"],
            "year": 2024,
            "journal": "测试期刊",
            "doi": "10.1234/test",
            "evidence_level": "⭐⭐⭐ 系统综述/Meta分析",
            "abstract": "这是一个测试摘要"
        }
    ]

    # 转换为字典
    state_dict = state.to_dict()
    assert "academic_papers" in state_dict, "状态字典中缺少academic_papers字段"
    assert len(state_dict["academic_papers"]) == 1, "学术论文数量不正确"
    logger.info("✅ 状态序列化包含学术论文")

    # 从字典恢复状态
    restored_state = State.from_dict(state_dict)
    assert len(restored_state.academic_papers) == 1, "恢复的学术论文数量不正确"
    assert restored_state.academic_papers[0]["title"] == "测试论文1", "恢复的论文标题不正确"
    logger.info("✅ 状态反序列化正确恢复学术论文")

def test_json_parsing():
    """测试JSON解析功能"""
    logger.info("测试3: JSON解析功能")

    from src.utils.text_processing import extract_clean_response

    # 测试标准JSON
    test_json = '{"title": "测试", "content": "内容"}'
    result = extract_clean_response(test_json)
    assert result["title"] == "测试", "标准JSON解析失败"
    logger.info("✅ 标准JSON解析通过")

    # 测试带格式问题的JSON
    problem_json = "{'title': '测试', 'content': '内容',}"
    result = extract_clean_response(problem_json)
    assert "title" in result, "格式问题JSON解析失败"
    logger.info("✅ 格式问题JSON解析通过")

def test_cache_functionality():
    """测试缓存功能"""
    logger.info("测试4: 缓存功能")

    from src.utils.cache import QueryCache

    cache = QueryCache()

    # 测试缓存设置和获取
    cache.set("test_key", {"result": "test_result"})
    cached_result = cache.get("test_key")
    assert cached_result == {"result": "test_result"}, "缓存设置和获取失败"
    logger.info("✅ 缓存设置和获取通过")

    # 测试缓存未命中
    missed_result = cache.get("non_existent_key")
    assert missed_result is None, "缓存未命中应该返回None"
    logger.info("✅ 缓存未命中正确返回None")

def test_sensitive_filter():
    """测试敏感词过滤功能"""
    logger.info("测试5: 敏感词过滤功能")

    from src.utils.evidence import filter_sensitive

    # 测试非敏感词
    assert filter_sensitive("人工智能研究") == False, "非敏感词应该返回False"
    logger.info("✅ 非敏感词过滤通过")

    # 测试敏感词
    assert filter_sensitive("堕胎研究") == True, "敏感词应该返回True"
    logger.info("✅ 敏感词检测通过")

def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("开始运行全流程测试")
    logger.info("=" * 60)

    try:
        test_config_validation()
        test_state_persistence()
        test_json_parsing()
        test_cache_functionality()
        test_sensitive_filter()

        logger.info("=" * 60)
        logger.info("✅ 所有测试通过！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}", exc_info=True)
        return False

    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
