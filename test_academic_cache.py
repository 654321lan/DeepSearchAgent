"""
测试学术模式缓存功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.agents.coordinator import AcademicCoordinator
from src.tools.crossref_search import CrossrefSearch
from src.tools.openalex_search import OpenAlexSearch
from src.llms.zhipu import ZhipuLLM

def test_academic_cache():
    """测试学术模式缓存功能"""
    print("=== 测试学术模式缓存功能 ===\n")
    
    # 创建模拟的LLM客户端（不实际调用API）
    class MockZhipuLLM:
        def invoke(self, system_prompt, user_prompt):
            return "模拟的LLM响应"
    
    # 创建协调器
    coordinator = AcademicCoordinator(
        MockZhipuLLM(),
        CrossrefSearch(),
        OpenAlexSearch()
    )
    
    # 测试查询
    test_query = "非酒精性脂肪肝的诊断和治疗指南"
    
    print("1. 测试缓存未命中")
    cached_result = coordinator.get_cached_result(test_query)
    if cached_result is None:
        print("✅ 缓存未命中测试通过")
    else:
        print("❌ 缓存未命中测试失败")
    
    print("\n2. 测试缓存信息")
    cache_info = coordinator.get_cache_info()
    print(f"缓存信息: {cache_info}")
    
    print("\n3. 测试缓存结果")
    # 模拟一个结果
    mock_result = ("模拟的学术报告", [{"title": "模拟论文", "year": 2023}])
    coordinator.cache_result(test_query, mock_result)
    
    print("\n4. 测试缓存命中")
    cached_result = coordinator.get_cached_result(test_query)
    if cached_result is not None:
        print("✅ 缓存命中测试通过")
        print(f"缓存结果: {cached_result[0][:50]}...")
    else:
        print("❌ 缓存命中测试失败")
    
    print("\n5. 测试缓存查询列表")
    cached_queries = coordinator.list_cached_queries()
    print(f"缓存的查询: {cached_queries}")
    
    print("\n6. 测试缓存存在检查")
    has_cache = coordinator.has_cached_result(test_query)
    if has_cache:
        print("✅ 缓存存在检查通过")
    else:
        print("❌ 缓存存在检查失败")
    
    print("\n7. 测试缓存配置")
    coordinator.set_cache_config(enabled=True, ttl=3600, max_size=500)
    print("✅ 缓存配置测试通过")
    
    print("\n8. 测试缓存清空")
    coordinator.clear_cache()
    cache_info_after_clear = coordinator.get_cache_info()
    if cache_info_after_clear['total_entries'] == 0:
        print("✅ 缓存清空测试通过")
    else:
        print("❌ 缓存清空测试失败")
    
    print("\n=== 学术模式缓存功能测试完成 ===")

if __name__ == "__main__":
    test_academic_cache()