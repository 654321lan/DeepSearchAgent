"""
综合测试所有修复
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.evidence import get_evidence_level, classify_study_type

def test_paper(paper_data, description):
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"{'='*60}")
    print(f"标题: {paper_data['title'][:60]}")
    print(f"期刊: {paper_data.get('journal', '未知')}")
    print(f"年份: {paper_data.get('year', '未知')}")

    try:
        study_type, confidence = classify_study_type(paper_data)
        print(f"研究类型: {study_type.value} (置信度: {confidence})")

        level, details = get_evidence_level(paper_data)
        print(f"初始等级: {details['initial_level']}")
        print(f"降级因素: 偏倚={details['risk_of_bias']}, 不精确={details['imprecision']}, 偏倚发表={details['publication_bias']}")
        print(f"总降级: {details['total_downgrade']}")
        print(f"最终等级: {details['final_level']}")

        # 测试grade_details是否为空
        if details and details.get('study_type'):
            print("✅ GRADE分级详情不为空")
        else:
            print("❌ GRADE分级详情为空！")

        # 测试降级逻辑
        if "RCT" in description or "指南" in description:
            if "低质量" in description:
                expected = "GRADE 极低级"
            else:
                expected = "GRADE 高级"
            if details['final_level'] == expected:
                print(f"✅ 降级逻辑正确")
            else:
                print(f"❌ 降级逻辑错误！期望: {expected}, 实际: {details['final_level']}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("="*60)
    print("综合测试所有修复")
    print("="*60)

    # 测试1: 高质量RCT
    test_paper({
        'title': 'A randomized, double-blind, placebo-controlled trial of semaglutide in patients with type 2 diabetes',
        'abstract': 'In this randomized, double-blind trial, we enrolled 500 patients with type 2 diabetes. Patients were randomly assigned to receive semaglutide or placebo.',
        'journal': 'Diabetes Care',
        'year': 2023
    }, "高质量RCT")

    # 测试2: 低质量RCT
    test_paper({
        'title': 'A randomized trial of drug X in patients with diabetes',
        'abstract': 'We conducted a study of drug X in 100 patients with type 2 diabetes. The treatment group received drug X, while the control group received placebo.',
        'journal': 'Journal of Small Medical Practice',
        'year': 2019
    }, "低质量RCT")

    # 测试3: 指南
    test_paper({
        'title': 'The diagnosis and management of nonalcoholic fatty liver disease: Practice guidance from the American Association for the Study of Liver Diseases',
        'abstract': 'This guideline provides a data-supported approach to the diagnosis and management of patients with nonalcoholic fatty liver disease.',
        'journal': 'Hepatology',
        'year': 2017
    }, "指南")

    # 测试4: 无摘要论文
    test_paper({
        'title': 'A study of medical treatment',
        'abstract': '',
        'journal': 'Unknown Journal',
        'year': 2020
    }, "无摘要论文")

    # 测试5: Meta分析
    test_paper({
        'title': 'Meta-analysis of antihypertensive drugs for blood pressure control',
        'abstract': 'We conducted a systematic review and meta-analysis of randomized controlled trials evaluating antihypertensive drugs. A total of 50 trials with 10,000 participants were included.',
        'journal': 'The Lancet',
        'year': 2022
    }, "Meta分析")

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()
