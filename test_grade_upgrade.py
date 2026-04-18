# -*- coding: utf-8 -*-
"""
测试GRADE分级升级功能
验证全链路溯源和决策卡生成
"""
import sys
import io

# 设置stdout为UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.utils.evidence import get_evidence_level, get_evidence_levels_batch, get_decision_card_display, GRADELevel

# 测试用例：包含不同类型的文献
test_papers = [
    {
        "title": "Randomized controlled trial of treatment for cardiovascular disease",
        "abstract": "This randomized controlled trial with double-blind design included 500 patients. The intervention showed a significant reduction in mortality (hazard ratio 0.45, p < 0.001). Large effect size with dose-response relationship observed. Confidence intervals were narrow (95% CI: 0.35-0.58).",
        "journal": "New England Journal of Medicine",
        "year": 2024
    },
    {
        "title": "Systematic review and meta-analysis of diabetes management",
        "abstract": "We conducted a systematic review and meta-analysis of 50 randomized controlled trials. The pooled analysis showed consistent results across studies (I2 = 15%). High quality evidence with significant benefits. Statistical power was adequate and all studies had proper blinding.",
        "journal": "Lancet Diabetes & Endocrinology",
        "year": 2025
    },
    {
        "title": "Cohort study examining risk factors for Alzheimer's disease",
        "abstract": "This prospective cohort study followed 2000 participants for 10 years. We observed a dose-response relationship between physical activity and cognitive decline. However, the study had a high dropout rate (30%) and wide confidence intervals. Results were statistically insignificant (p > 0.05).",
        "journal": "Journal of Neurology",
        "year": 2023
    },
    {
        "title": "Case-control study of environmental risk factors",
        "abstract": "A case-control study with 150 cases and 150 controls. The study had selection bias and small sample size. No adjustment for confounding factors was made. Results showed inconsistent findings across subgroups.",
        "journal": "Environmental Health Perspectives",
        "year": 2022
    },
    {
        "title": "Expert opinion on rare disease treatment",
        "abstract": "This is an expert opinion article based on clinical experience. No systematic review was conducted. The recommendations are based on limited evidence from case reports.",
        "journal": "Journal of Rare Diseases",
        "year": 2024
    }
]

def test_single_paper_grading():
    """测试单篇论文的GRADE分级"""
    print("=" * 80)
    print("测试1：单篇论文GRADE分级（包含决策卡）")
    print("=" * 80)
    print()

    for i, paper in enumerate(test_papers, 1):
        print(f"{'='*80}")
        print(f"测试论文 {i}: {paper['title']}")
        print(f"{'='*80}")

        try:
            # 调用GRADE分级
            level, details = get_evidence_level(paper)

            print(f"\n最终等级: {details['final_level']}")
            print(f"初始等级: {details['initial_level']}")
            print(f"净调整值: {details['net_adjustment']:+d}")
            print(f"计算步骤:")
            for step in details['calculation_steps']:
                print(f"  - {step}")

            # 显示决策卡
            print("\n" + "="*80)
            print("GRADE 分级决策卡")
            print("="*80)
            decision_card_display = get_decision_card_display(details)
            print(decision_card_display)

        except Exception as e:
            print(f"[X] 分级失败: {e}")
            import traceback
            traceback.print_exc()

        print()

def test_batch_grading():
    """测试批量GRADE分级"""
    print("=" * 80)
    print("测试2：批量GRADE分级")
    print("=" * 80)
    print()

    try:
        results = get_evidence_levels_batch(test_papers)

        print(f"成功处理 {len(results)} 篇论文\n")

        for i, (level, details) in enumerate(results, 1):
            print(f"{i}. {test_papers[i-1]['title'][:50]}...")
            print(f"   初始等级: {details['initial_level']}")
            print(f"   最终等级: {details['final_level']} (调整: {details['net_adjustment']:+d})")
            print(f"   升级因素: {len(details['upgrade_factors'])}个")
            print(f"   降级因素: {len(details['downgrade_factors'])}个")
            print()

    except Exception as e:
        print(f"[X] 批量分级失败: {e}")
        import traceback
        traceback.print_exc()

def test_upgrade_downgrade_factors():
    """测试升降级因素识别"""
    print("=" * 80)
    print("测试3：升降级因素识别")
    print("=" * 80)
    print()

    # 测试包含多种升降级因素的论文
    complex_paper = {
        "title": "Comprehensive study with multiple factors",
        "abstract": """
        This randomized controlled trial had a small sample size (n=30) and wide confidence intervals.
        However, it demonstrated a highly significant effect with hazard ratio 0.35 (p < 0.001).
        The study showed a clear dose-response relationship.
        There was no blinding and high dropout rate (40%).
        The research was industry-funded.
        Adjusted for multiple confounders using multivariate analysis.
        Results were consistent across subgroups.
        """,
        "journal": "Test Journal",
        "year": 2024
    }

    level, details = get_evidence_level(complex_paper)

    print("升级因素:")
    for factor in details['upgrade_factors']:
        print(f"  - {factor['name']} ({factor['strength']})")
        print(f"    匹配文本: {factor['matched_text']}")
        print(f"    上下文: {factor['context']}")
        print()

    print("\n降级因素:")
    for factor in details['downgrade_factors']:
        print(f"  - {factor['name']} ({factor['strength']})")
        print(f"    匹配文本: {factor['matched_text']}")
        print(f"    上下文: {factor['context']}")
        print()

    print(f"\n净调整值: {details['net_adjustment']:+d}")
    print(f"初始等级: {details['initial_level']}")
    print(f"最终等级: {details['final_level']}")

def test_decision_card_structure():
    """测试决策卡结构完整性"""
    print("\n" + "=" * 80)
    print("测试4：决策卡结构完整性")
    print("=" * 80)
    print()

    level, details = get_evidence_level(test_papers[0])
    decision_card = details.get('decision_card')

    if decision_card:
        required_fields = [
            'paper_title', 'paper_journal', 'paper_year',
            'initial_study_type', 'initial_level', 'initial_reason', 'matched_pattern',
            'upgrade_factors', 'downgrade_factors', 'net_adjustment',
            'final_level', 'adjustment_path',
            'applicable_scenarios', 'limitations',
            'original_level_str'
        ]

        print("检查决策卡字段:")
        all_present = True
        for field in required_fields:
            present = field in decision_card
            status = "[OK]" if present else "[X]"
            print(f"  {status} {field}")
            if not present:
                all_present = False

        print()
        if all_present:
            print("[OK] 所有必需字段都存在")
        else:
            print("[X] 部分字段缺失")
    else:
        print("[X] 决策卡未生成")

def test_compatibility():
    """测试向后兼容性"""
    print("\n" + "=" * 80)
    print("测试5：向后兼容性（原始等级字符串）")
    print("=" * 80)
    print()

    level, details = get_evidence_level(test_papers[0])

    # 检查是否保留了原始等级字符串
    original_level_str = details.get('decision_card', {}).get('original_level_str')
    final_level = details.get('final_level')

    print(f"final_level: {final_level}")
    print(f"original_level_str: {original_level_str}")

    if final_level == original_level_str:
        print("[OK] 原始等级字符串正确保留")
    else:
        print("[X] 原始等级字符串不匹配")

    # 检查GRADEDetailedDecisionCard对象
    if isinstance(level, GRADELevel):
        print(f"[OK] 返回的level是GRADELevel枚举类型: {level}")
    else:
        print(f"[X] 返回的level类型不正确: {type(level)}")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("GRADE分级升级功能测试套件")
    print("="*80)
    print()

    # 运行所有测试
    test_single_paper_grading()
    test_batch_grading()
    test_upgrade_downgrade_factors()
    test_decision_card_structure()
    test_compatibility()

    print("\n" + "="*80)
    print("[OK] 所有测试完成")
    print("="*80)
