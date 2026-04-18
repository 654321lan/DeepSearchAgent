# -*- coding: utf-8 -*-
"""
GRADE分级升级功能演示
展示全链路溯源和决策卡功能
"""
import sys
import io

# 设置stdout为UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.utils.evidence import get_evidence_level, get_decision_card_display

def demo_single_paper():
    """演示单篇论文的完整GRADE分级流程"""
    print("=" * 80)
    print("演示1：单篇论文GRADE分级")
    print("=" * 80)
    print()

    # 一篇高质量RCT论文
    paper = {
        "title": "Randomized controlled trial of novel treatment for heart failure",
        "abstract": """
        This randomized, double-blind, placebo-controlled trial enrolled 500 patients
        with chronic heart failure. The intervention group received the novel treatment
        while the control group received standard care.

        Results:
        - Significant reduction in all-cause mortality (hazard ratio 0.45, 95% CI: 0.35-0.58, p < 0.001)
        - Clear dose-response relationship observed across treatment doses
        - Large effect size consistent across all subgroups
        - No significant adverse events reported

        The study had adequate statistical power (80%) to detect the primary endpoint.
        Confidence intervals were narrow, indicating precise estimates.
        """,
        "journal": "New England Journal of Medicine",
        "year": 2024
    }

    print("论文信息:")
    print(f"  标题: {paper['title']}")
    print(f"  期刊: {paper['journal']}")
    print(f"  年份: {paper['year']}")
    print()

    # 执行GRADE分级
    level, details = get_evidence_level(paper)

    print("分级结果:")
    print(f"  初始等级: {details['initial_level']}")
    print(f"  净调整值: {details['net_adjustment']:+d}")
    print(f"  最终等级: {details['final_level']}")
    print()

    # 显示完整决策卡
    decision_card = get_decision_card_display(details)
    print(decision_card)

def demo_complex_paper():
    """演示复杂论文的升降级因素识别"""
    print("=" * 80)
    print("演示2：复杂论文的升降级因素识别")
    print("=" * 80)
    print()

    # 一篇包含多种升降级因素的论文
    paper = {
        "title": "Mixed-quality study of treatment effectiveness",
        "abstract": """
        This randomized controlled trial investigated a new treatment approach.
        However, the study had several methodological limitations:

        Limitations:
        - Small sample size (n=30) limited statistical power
        - Wide confidence intervals (95% CI: 0.2-2.5) indicating imprecision
        - High dropout rate (40%) during follow-up
        - Lack of blinding for investigators
        - Industry funding with potential conflict of interest

        Positive findings:
        - Highly significant treatment effect (p < 0.001)
        - Large effect size with hazard ratio 0.35
        - Clear dose-response relationship
        - Adjusted for multiple confounders using multivariate analysis
        - Consistent results across different subgroups
        """,
        "journal": "Journal of Medical Research",
        "year": 2023
    }

    print("论文信息:")
    print(f"  标题: {paper['title']}")
    print()

    # 执行GRADE分级
    level, details = get_evidence_level(paper)

    print("分级结果:")
    print(f"  初始等级: {details['initial_level']}")
    print(f"  净调整值: {details['net_adjustment']:+d}")
    print(f"  最终等级: {details['final_level']}")
    print()

    print("升级因素详情:")
    for i, factor in enumerate(details['upgrade_factors'], 1):
        print(f"  {i}. {factor['name']} ({factor['strength']})")
        print(f"     匹配文本: {factor['matched_text']}")
        print(f"     上下文: {factor['context']}")
        print()

    print("降级因素详情:")
    for i, factor in enumerate(details['downgrade_factors'], 1):
        print(f"  {i}. {factor['name']} ({factor['strength']})")
        print(f"     匹配文本: {factor['matched_text']}")
        print(f"     上下文: {factor['context']}")
        print()

    print("调整路径:")
    print(f"  {details['decision_card']['adjustment_path']}")
    print()

def demo_different_study_types():
    """演示不同研究类型的分级"""
    print("=" * 80)
    print("演示3：不同研究类型的GRADE分级")
    print("=" * 80)
    print()

    papers = [
        {
            "title": "Systematic review and meta-analysis of diabetes treatment",
            "abstract": "Comprehensive systematic review of 50 randomized controlled trials. Pooled analysis showed consistent benefits across studies with low heterogeneity (I2=12%). All studies had adequate blinding and proper randomization.",
            "type": "系统综述"
        },
        {
            "title": "Randomized controlled trial of hypertension treatment",
            "abstract": "This randomized controlled trial demonstrated significant blood pressure reduction (p<0.01). However, the study had a moderate dropout rate (15%) and wide confidence intervals.",
            "type": "随机对照试验"
        },
        {
            "title": "Prospective cohort study of cancer risk factors",
            "abstract": "This cohort study followed 2000 participants for 10 years. We observed a dose-response relationship between smoking and cancer risk. The study had a high dropout rate (25%) and results were statistically insignificant.",
            "type": "队列研究"
        },
        {
            "title": "Case-control study of environmental exposure",
            "abstract": "A case-control study with 100 cases and 100 controls. The study had selection bias and small sample size. No adjustment for confounding factors was made.",
            "type": "病例对照研究"
        },
        {
            "title": "Expert opinion on rare disease management",
            "abstract": "This expert opinion article provides recommendations based on clinical experience. No systematic review was conducted.",
            "type": "专家意见"
        }
    ]

    for paper in papers:
        level, details = get_evidence_level(paper)
        print(f"{paper['type']:12s} | {details['initial_level']:12s} -> {details['final_level']:12s} (调整: {details['net_adjustment']:+2d})")

    print()

def demo_applicable_scenarios():
    """演示不同证据等级的适用场景"""
    print("=" * 80)
    print("演示4：不同证据等级的适用场景")
    print("=" * 80)
    print()

    from src.utils.evidence import (
        GRADELevel,
        APPLICABLE_SCENARIOS_MAP,
        LIMITATIONS_MAP
    )

    for level in [GRADELevel.HIGH, GRADELevel.MODERATE, GRADELevel.LOW, GRADELevel.VERY_LOW]:
        print(f"{level.value}:")
        print(f"  适用场景:")
        for scenario in APPLICABLE_SCENARIOS_MAP[level]:
            print(f"    • {scenario}")
        print(f"  局限性:")
        for limitation in LIMITATIONS_MAP[level]:
            print(f"    • {limitation}")
        print()

if __name__ == "__main__":
    print()
    print("=" * 80)
    print("GRADE分级升级功能演示")
    print("=" * 80)
    print()

    demo_single_paper()
    demo_complex_paper()
    demo_different_study_types()
    demo_applicable_scenarios()

    print("=" * 80)
    print("演示完成！")
    print("=" * 80)
    print()
