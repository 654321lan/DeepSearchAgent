"""
测试应该降级的RCT
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.evidence import get_evidence_level, classify_study_type, StudyType

def main():
    print("=== 测试应该降级的RCT ===")

    # 测试低质量RCT论文数据
    test_paper = {
        'title': 'A study of drug X in patients with diabetes',
        'abstract': 'We studied 50 patients with diabetes who received drug X. The treatment was administered for 12 weeks. Patients showed improvement in their condition.',
        'journal': 'Journal of Local Medical Research',
        'year': 2020
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
