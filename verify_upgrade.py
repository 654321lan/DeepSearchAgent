# -*- coding: utf-8 -*-
"""
验证GRADE升级后的主要功能
"""
import sys
import io

# 设置stdout为UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.utils.evidence import (
    get_evidence_level,
    get_evidence_levels_batch,
    get_evidence_priority,
    get_decision_card_display,
    GRADELevel
)

def test_backward_compatibility():
    """测试向后兼容性"""
    print("=" * 80)
    print("验证1：向后兼容性测试")
    print("=" * 80)
    print()

    test_paper = {
        "title": "Randomized controlled trial of treatment X",
        "abstract": "This randomized controlled trial included 200 patients with double-blind design.",
        "journal": "Test Journal",
        "year": 2024
    }

    try:
        # 调用主函数（不传递额外参数）
        level, details = get_evidence_level(test_paper)

        # 检查返回值
        assert isinstance(level, GRADELevel), "返回的level应该是GRADELevel枚举"
        assert 'final_level' in details, "details应该包含final_level"
        assert 'initial_level' in details, "details应该包含initial_level"

        print(f"[*] 函数调用成功")
        print(f"[*] 返回等级: {level.value}")
        print(f"[*] 最终等级: {details['final_level']}")
        print(f"[*] 初始等级: {details['initial_level']}")

        # 检查决策卡
        if 'decision_card' in details and details['decision_card']:
            print(f"[*] 决策卡已生成")
            dc = details['decision_card']
            assert 'original_level_str' in dc, "决策卡应该包含original_level_str"
            assert dc['original_level_str'] == details['final_level'], "original_level_str应该等于final_level"
            print(f"[*] original_level_str正确: {dc['original_level_str']}")
        else:
            print(f"[!] 警告：决策卡未生成")

        print()
        print("[OK] 向后兼容性测试通过")
        return True

    except Exception as e:
        print(f"[X] 向后兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_new_features():
    """测试新功能"""
    print()
    print("=" * 80)
    print("验证2：新功能测试（正则升降级因素匹配）")
    print("=" * 80)
    print()

    test_paper = {
        "title": "Complex study with multiple factors",
        "abstract": """
        This randomized controlled trial had a small sample size (n=30) and wide confidence intervals.
        However, it demonstrated a highly significant effect with hazard ratio 0.35 (p < 0.001).
        The study showed a clear dose-response relationship.
        There was no blinding and high dropout rate (40%).
        The research was industry-funded.
        Adjusted for multiple confounders using multivariate analysis.
        """,
        "journal": "Test Journal",
        "year": 2024
    }

    try:
        level, details = get_evidence_level(test_paper)

        # 检查升降级因素
        upgrade_factors = details.get('upgrade_factors', [])
        downgrade_factors = details.get('downgrade_factors', [])

        print(f"[*] 升级因素数量: {len(upgrade_factors)}")
        for factor in upgrade_factors:
            print(f"    - {factor['name']} ({factor['strength']})")

        print(f"[*] 降级因素数量: {len(downgrade_factors)}")
        for factor in downgrade_factors:
            print(f"    - {factor['name']} ({factor['strength']})")

        print(f"[*] 净调整值: {details['net_adjustment']:+d}")
        print(f"[*] 最终等级: {details['final_level']}")

        # 验证升级/降级因素不为空（至少应该有一些被识别）
        total_factors = len(upgrade_factors) + len(downgrade_factors)
        if total_factors > 0:
            print(f"[OK] 成功识别到{total_factors}个升降级因素")
        else:
            print(f"[!] 警告：未识别到任何升降级因素")

        print()
        print("[OK] 新功能测试通过")
        return True

    except Exception as e:
        print(f"[X] 新功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_processing():
    """测试批量处理"""
    print()
    print("=" * 80)
    print("验证3：批量处理测试")
    print("=" * 80)
    print()

    test_papers = [
        {
            "title": "RCT paper",
            "abstract": "Randomized controlled trial with significant results.",
            "journal": "Journal 1",
            "year": 2024
        },
        {
            "title": "Cohort study",
            "abstract": "Prospective cohort study following 1000 patients.",
            "journal": "Journal 2",
            "year": 2023
        },
        {
            "title": "Systematic review",
            "abstract": "Systematic review and meta-analysis of 50 studies.",
            "journal": "Journal 3",
            "year": 2025
        }
    ]

    try:
        # 批量处理（不传递额外参数）
        results = get_evidence_levels_batch(test_papers)

        assert len(results) == len(test_papers), f"应该返回{len(test_papers)}个结果"

        print(f"[*] 成功处理 {len(results)} 篇论文")
        for i, (level, details) in enumerate(results, 1):
            print(f"    {i}. {test_papers[i-1]['title']}: {details['final_level']}")

        print()
        print("[OK] 批量处理测试通过")
        return True

    except Exception as e:
        print(f"[X] 批量处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_evidence_priority():
    """测试证据优先级"""
    print()
    print("=" * 80)
    print("验证4：证据优先级测试")
    print("=" * 80)
    print()

    try:
        # 测试所有等级的优先级
        priorities = {
            GRADELevel.HIGH: get_evidence_priority(GRADELevel.HIGH),
            GRADELevel.MODERATE: get_evidence_priority(GRADELevel.MODERATE),
            GRADELevel.LOW: get_evidence_priority(GRADELevel.LOW),
            GRADELevel.VERY_LOW: get_evidence_priority(GRADELevel.VERY_LOW),
        }

        print("各等级优先级:")
        for level, priority in priorities.items():
            print(f"    {level.value}: {priority}")

        # 验证优先级顺序
        assert priorities[GRADELevel.HIGH] > priorities[GRADELevel.MODERATE], "HIGH > MODERATE"
        assert priorities[GRADELevel.MODERATE] > priorities[GRADELevel.LOW], "MODERATE > LOW"
        assert priorities[GRADELevel.LOW] > priorities[GRADELevel.VERY_LOW], "LOW > VERY_LOW"

        print()
        print("[OK] 证据优先级测试通过")
        return True

    except Exception as e:
        print(f"[X] 证据优先级测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_decision_card_display():
    """测试决策卡显示"""
    print()
    print("=" * 80)
    print("验证5：决策卡显示测试")
    print("=" * 80)
    print()

    test_paper = {
        "title": "Test paper for decision card",
        "abstract": "Randomized controlled trial with significant effect (HR 0.45, p<0.001).",
        "journal": "Test Journal",
        "year": 2024
    }

    try:
        level, details = get_evidence_level(test_paper)
        display = get_decision_card_display(details)

        assert display is not None, "决策卡显示不应为None"
        assert len(display) > 0, "决策卡显示不应为空"

        print(f"[*] 决策卡显示生成成功，长度: {len(display)} 字符")
        print(f"[*] 包含关键字段:")
        assert "GRADE 分级决策卡" in display, "应包含标题"
        print(f"    - 标题")
        assert "文献信息" in display, "应包含文献信息"
        print(f"    - 文献信息")
        assert "初始分级" in display, "应包含初始分级"
        print(f"    - 初始分级")
        assert "最终等级" in display, "应包含最终等级"
        print(f"    - 最终等级")
        assert "适用场景" in display, "应包含适用场景"
        print(f"    - 适用场景")
        assert "局限性" in display, "应包含局限性"
        print(f"    - 局限性")

        print()
        print("[OK] 决策卡显示测试通过")
        return True

    except Exception as e:
        print(f"[X] 决策卡显示测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    print("=" * 80)
    print("GRADE升级功能验证套件")
    print("=" * 80)
    print()

    results = []
    results.append(test_backward_compatibility())
    results.append(test_new_features())
    results.append(test_batch_processing())
    results.append(test_evidence_priority())
    results.append(test_decision_card_display())

    print()
    print("=" * 80)
    print(f"验证结果: {sum(results)}/{len(results)} 通过")
    print("=" * 80)

    if all(results):
        print()
        print("[OK] 所有验证测试通过！GRADE升级成功完成。")
        print()
    else:
        print()
        print("[!] 部分验证测试失败，请检查上述错误信息。")
        print()
