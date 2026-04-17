"""
调试测试：检查证据等级计算和总结生成问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.evidence import get_evidence_level, classify_study_type, StudyType

def test_evidence_level():
    """测试证据等级计算"""
    print("=== 测试证据等级计算 ===")
    
    # 测试论文数据
    test_paper = {
        'title': 'The diagnosis and management of nonalcoholic fatty liver disease: Practice guidance from the American Association for the Study of Liver Diseases',
        'abstract': 'This guideline provides a data-supported approach to the diagnosis and management of patients with nonalcoholic fatty liver disease.',
        'journal': 'Hepatology',
        'year': 2017
    }
    
    print(f"论文标题: {test_paper['title']}")
    print(f"期刊: {test_paper['journal']}")
    print(f"年份: {test_paper['year']}")
    
    # 测试研究类型分类
    print("\n1. 测试研究类型分类:")
    try:
        study_type, confidence = classify_study_type(test_paper)
        print(f"研究类型: {study_type.value} (置信度: {confidence})")
    except Exception as e:
        print(f"研究类型分类错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试证据等级计算
    print("\n2. 测试证据等级计算:")
    try:
        level, details = get_evidence_level(test_paper)
        print(f"证据等级: {level.value}")
        print(f"分级详情: {details}")
    except Exception as e:
        print(f"证据等级计算错误: {e}")
        import traceback
        traceback.print_exc()

def test_regex_patterns():
    """测试正则表达式模式"""
    print("\n=== 测试正则表达式模式 ===")
    
    test_cases = [
        "The diagnosis and management of nonalcoholic fatty liver disease: Practice guidance",
        "systematic review and meta-analysis",
        "randomized controlled trial",
        "guideline for diagnosis"
    ]
    
    for text in test_cases:
        print(f"\n测试文本: {text}")
        
        # 测试每个模式
        patterns = [
            ("systematic_review_meta", r"(systematic review|meta[- ]analysis|荟萃分析|系统综述|guideline|指南)"),
            ("rct", r"(randomized|randomised|rct|随机对照试验|随机.*双盲|随机.*安慰剂)"),
            ("guideline", r"(guideline|指南)")
        ]
        
        for pattern_name, pattern in patterns:
            import re
            if re.search(pattern, text, re.IGNORECASE):
                print(f"  ✓ 匹配到 {pattern_name}: {pattern}")

def test_evidence_agent():
    """测试证据代理"""
    print("\n=== 测试证据代理 ===")
    
    from src.agents.evidence_agent import EvidenceAgent
    
    # 创建证据代理
    agent = EvidenceAgent("TestEvidenceAgent")
    
    # 测试论文数据
    papers = [
        {
            'title': 'The diagnosis and management of nonalcoholic fatty liver disease: Practice guidance',
            'abstract': 'This guideline provides a data-supported approach',
            'journal': 'Hepatology',
            'year': 2017,
            'doi': '10.1002/hep.29367'
        }
    ]
    
    try:
        result = agent.process({'papers': papers})
        print(f"证据代理处理结果: {result['status']}")
        if result['status'] == 'success':
            for paper in result['papers']:
                print(f"  - 标题: {paper['title'][:50]}...")
                print(f"    证据等级: {paper.get('evidence_level', '未设置')}")
                print(f"    证据片段: {paper.get('evidence_snippets', [])}")
    except Exception as e:
        print(f"证据代理错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_evidence_level()
    test_regex_patterns()
    test_evidence_agent()