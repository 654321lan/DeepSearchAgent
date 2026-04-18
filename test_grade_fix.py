"""
测试修复后的GRADE证据分级模块
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.evidence import get_evidence_level, StudyType, GRADELevel

def test_grade_fix():
    """测试GRADE证据分级修复"""
    print("=== 测试GRADE证据分级修复 ===")
    
    # 测试案例1：指南类文献（应该标为高级）
    guideline_paper = {
        'title': 'The diagnosis and management of nonalcoholic fatty liver disease: Practice guidance from the American Association for the Study of Liver Diseases',
        'abstract': 'This guideline provides a data-supported approach to the diagnosis and management of patients with nonalcoholic fatty liver disease.',
        'journal': 'Hepatology',
        'year': 2017
    }
    
    print("\n1. 测试指南类文献：")
    print(f"标题: {guideline_paper['title']}")
    print(f"期刊: {guideline_paper['journal']}")
    
    level, details = get_evidence_level(guideline_paper)
    print(f"证据等级: {level.value}")
    print(f"研究类型: {details['study_type']}")
    print(f"初始等级: {details['initial_level']}")
    print(f"最终等级: {details['final_level']}")
    print(f"分类原因: {details['classification_reason']}")
    print(f"降级原因: {details['downgrade_reasons']}")
    
    # 测试案例2：RCT文献（应该标为高级）
    rct_paper = {
        'title': 'A randomized controlled trial of metformin in patients with nonalcoholic fatty liver disease',
        'abstract': 'This randomized, double-blind, placebo-controlled trial enrolled 300 patients with NAFLD to assess the efficacy of metformin.',
        'journal': 'New England Journal of Medicine',
        'year': 2020
    }
    
    print("\n2. 测试RCT文献：")
    print(f"标题: {rct_paper['title']}")
    
    level, details = get_evidence_level(rct_paper)
    print(f"证据等级: {level.value}")
    print(f"研究类型: {details['study_type']}")
    print(f"初始等级: {details['initial_level']}")
    
    # 测试案例3：队列研究（应该标为中级）
    cohort_paper = {
        'title': 'A prospective cohort study of cardiovascular risk in patients with fatty liver disease',
        'abstract': 'This prospective cohort study followed 500 patients for 5 years to assess cardiovascular outcomes.',
        'journal': 'Journal of Clinical Gastroenterology',
        'year': 2019
    }
    
    print("\n3. 测试队列研究：")
    print(f"标题: {cohort_paper['title']}")
    
    level, details = get_evidence_level(cohort_paper)
    print(f"证据等级: {level.value}")
    print(f"研究类型: {details['study_type']}")
    print(f"初始等级: {details['initial_level']}")
    
    # 测试案例4：病例对照研究（应该标为低级）
    case_control_paper = {
        'title': 'A case-control study of genetic factors in fatty liver disease',
        'abstract': 'This case-control study compared 200 patients with NAFLD to 200 healthy controls.',
        'journal': 'Liver International',
        'year': 2018
    }
    
    print("\n4. 测试病例对照研究：")
    print(f"标题: {case_control_paper['title']}")
    
    level, details = get_evidence_level(case_control_paper)
    print(f"证据等级: {level.value}")
    print(f"研究类型: {details['study_type']}")
    print(f"初始等级: {details['initial_level']}")
    
    # 测试案例5：观察性研究（应该标为极低级）
    observational_paper = {
        'title': 'An observational study of lifestyle factors in fatty liver disease',
        'abstract': 'This cross-sectional study examined lifestyle factors in 100 patients with NAFLD.',
        'journal': 'Clinical Research',
        'year': 2021
    }
    
    print("\n5. 测试观察性研究：")
    print(f"标题: {observational_paper['title']}")
    
    level, details = get_evidence_level(observational_paper)
    print(f"证据等级: {level.value}")
    print(f"研究类型: {details['study_type']}")
    print(f"初始等级: {details['initial_level']}")
    
    # 测试案例6：无摘要文献（仅用标题）
    no_abstract_paper = {
        'title': 'Systematic review and meta-analysis of treatment options for NAFLD',
        'abstract': '',  # 空摘要
        'journal': 'Cochrane Database',
        'year': 2022
    }
    
    print("\n6. 测试无摘要文献：")
    print(f"标题: {no_abstract_paper['title']}")
    print(f"摘要: {no_abstract_paper['abstract']}")
    
    level, details = get_evidence_level(no_abstract_paper)
    print(f"证据等级: {level.value}")
    print(f"研究类型: {details['study_type']}")
    print(f"初始等级: {details['initial_level']}")
    print(f"分类原因: {details['classification_reason']}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_grade_fix()