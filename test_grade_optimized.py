"""
测试优化后的GRADE证据分级模块（两步分级标准）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.evidence import get_evidence_level, get_evidence_levels_batch, GRADELevel

def test_grade_optimized():
    """测试优化后的GRADE证据分级"""
    print("=== 测试优化后的GRADE证据分级（两步分级标准） ===")
    
    # 测试文献数据
    test_papers = [
        {
            'title': 'The diagnosis and management of nonalcoholic fatty liver disease: Practice guidance from the American Association for the Study of Liver Diseases',
            'abstract': 'This guideline provides a data-supported approach to the diagnosis and management of patients with nonalcoholic fatty liver disease.',
            'journal': 'Hepatology',
            'year': 2017
        },
        {
            'title': 'A randomized controlled trial of metformin in patients with nonalcoholic fatty liver disease',
            'abstract': 'This randomized, double-blind, placebo-controlled trial enrolled 300 patients with NAFLD to assess the efficacy of metformin.',
            'journal': 'New England Journal of Medicine',
            'year': 2020
        },
        {
            'title': 'A prospective cohort study of cardiovascular risk in patients with fatty liver disease',
            'abstract': 'This prospective cohort study followed 500 patients for 5 years to assess cardiovascular outcomes.',
            'journal': 'Journal of Clinical Gastroenterology',
            'year': 2019
        },
        {
            'title': 'A case-control study of genetic factors in fatty liver disease',
            'abstract': 'This case-control study compared 200 patients with NAFLD to 200 healthy controls.',
            'journal': 'Liver International',
            'year': 2018
        },
        {
            'title': 'An observational study of lifestyle factors in fatty liver disease',
            'abstract': 'This cross-sectional study examined lifestyle factors in 100 patients with NAFLD.',
            'journal': 'Clinical Research',
            'year': 2021
        }
    ]
    
    print("\n1. 测试单篇文献分级（无LLM调整）：")
    paper = test_papers[0]
    print(f"标题: {paper['title']}")
    
    level, details = get_evidence_level(paper)
    print(f"初始等级: {details['initial_level']}")
    print(f"初始原因: {details['initial_reason']}")
    print(f"LLM调整: {details['llm_adjustment']}")
    print(f"最终等级: {details['final_level']}")
    print(f"计算步骤: {details['calculation_steps']}")
    
    print("\n2. 测试批量文献分级（无LLM调整）：")
    results = get_evidence_levels_batch(test_papers)
    
    for i, (level, details) in enumerate(results):
        print(f"\n文献{i+1}: {test_papers[i]['title'][:50]}...")
        print(f"  初始等级: {details['initial_level']}")
        print(f"  最终等级: {details['final_level']}")
        print(f"  LLM调整: {details['llm_adjustment']}")
    
    print("\n3. 验证GRADE标准符合性：")
    expected_levels = [
        ("指南类文献", "GRADE 高级"),
        ("RCT文献", "GRADE 高级"),
        ("队列研究", "GRADE 中级"),
        ("病例对照", "GRADE 低级"),
        ("观察性研究", "GRADE 极低级")
    ]
    
    for i, (expected_type, expected_level) in enumerate(expected_levels):
        actual_level = results[i][1]['final_level']
        status = "✅" if actual_level == expected_level else "❌"
        print(f"{status} {expected_type}: 期望{expected_level}，实际{actual_level}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_grade_optimized()