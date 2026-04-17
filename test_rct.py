"""
测试RCT证据等级计算
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.evidence import get_evidence_level, classify_study_type, StudyType

def main():
    print("=== 测试RCT证据等级计算 ===")

    # 测试RCT论文数据
    test_paper = {
        'title': 'A randomized, double-blind, placebo-controlled trial of semaglutide in patients with type 2 diabetes',
        'abstract': 'In this randomized, double-blind trial, we enrolled 500 patients with type 2 diabetes. Patients were randomly assigned to receive semaglutide or placebo. The primary endpoint was reduction in HbA1c. At 26 weeks, the semaglutide group showed a significantly greater reduction in HbA1c compared to placebo.',
        'journal': 'Diabetes Care',
        'year': 2023
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
        print(f"分级详情:")
        for key, value in details.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"证据等级计算错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
