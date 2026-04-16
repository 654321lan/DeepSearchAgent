"""
证据处理工具函数（改进版）
"""

import re
from typing import Tuple

# 新增：常量定义（方便维护）
GRADE_CONFIG = {
    'high': {'keywords': [r'systematic review|meta-analysis', r'guideline|consensus|practice guideline'], 'priority': 4, 'base_score': 80},
    'medium': {'keywords': [r'randomized controlled trial|rct'], 'priority': 3, 'base_score': 60},
    'low': {'keywords': [r'prospective cohort|cohort study', r'case-control'], 'priority': 2, 'base_score': 40},
    'very_low': {'keywords': [r'cross-sectional', r'case report|case series'], 'priority': 1, 'base_score': 20},
    'default': {'priority': 1, 'base_score': 20}
}
DOWNGRADE_FACTORS = {
    'year_threshold': 2015,
    'sample_size_threshold': 100,
    'require_journal': True
}
CURRENT_YEAR = 2026  # 抽成常量

# 新增：通用函数 - 获取初始等级和优先级
def _get_initial_grade_info(title_abs: str) -> tuple[str, str, int]:
    """内部函数：获取初始的GRADE等级、研究类型、优先级"""
    title_abs_lower = title_abs.lower()
    
    # 高等级
    for kw in GRADE_CONFIG['high']['keywords']:
        if re.search(kw, title_abs_lower):
            if 'systematic review' in kw or 'meta-analysis' in kw:
                return "高", "系统综述/Meta分析", GRADE_CONFIG['high']['priority']
            else:
                return "高", "临床指南/共识", GRADE_CONFIG['high']['priority']
    
    # 中等级
    for kw in GRADE_CONFIG['medium']['keywords']:
        if re.search(kw, title_abs_lower):
            return "中", "随机对照试验(RCT)", GRADE_CONFIG['medium']['priority']
    
    # 低等级
    for kw in GRADE_CONFIG['low']['keywords']:
        if re.search(kw, title_abs_lower):
            if 'cohort' in kw:
                return "低", "前瞻性队列研究", GRADE_CONFIG['low']['priority']
            else:
                return "低", "病例对照研究", GRADE_CONFIG['low']['priority']
    
    # 极低等级
    for kw in GRADE_CONFIG['very_low']['keywords']:
        if re.search(kw, title_abs_lower):
            if 'cross-sectional' in kw:
                return "极低", "横断面研究", GRADE_CONFIG['very_low']['priority']
            else:
                return "极低", "病例报告/病例系列", GRADE_CONFIG['very_low']['priority']
    
    # 默认
    return "极低", "其他研究", GRADE_CONFIG['default']['priority']

# 新增：通用函数 - 计算降级次数
def _get_downgrade_count(paper: dict) -> int:
    """内部函数：计算降级因素数量"""
    downgrade_count = 0
    year = paper.get('year', 0) or 0
    sample_size = paper.get('sample_size', 0) or 0
    journal = paper.get('journal', '') or ''
    
    # 降级因素1：发表年份早于阈值
    if year < DOWNGRADE_FACTORS['year_threshold']:
        downgrade_count += 1
    
    # 降级因素2：样本量不足
    if sample_size > 0 and sample_size < DOWNGRADE_FACTORS['sample_size_threshold']:
        downgrade_count += 1
    
    # 降级因素3：无期刊信息
    if DOWNGRADE_FACTORS['require_journal'] and (not journal or journal.strip() == ''):
        downgrade_count += 1
    
    return downgrade_count

# 优化：重构后的 get_evidence_level
def get_evidence_level(paper: dict) -> str:
    """
    根据论文信息判断证据等级（基于GRADE金标准）
    返回：等级描述字符串，如 "GRADE 高级 | 临床指南"
    """
    title = paper.get('title', '').lower()
    abstract = paper.get('abstract', '').lower()
    title_abs = title + " " + abstract
    
    # 初始等级
    grade_level, study_type, priority = _get_initial_grade_info(title_abs)
    
    # 计算降级次数
    downgrade_count = _get_downgrade_count(paper)
    
    # 根据降级因素调整等级（仅调整等级描述，优先级单独处理）
    if downgrade_count > 0:
        if grade_level == "高":
            if downgrade_count >= 2:
                grade_level = "低"
            else:
                grade_level = "中"
        elif grade_level == "中":
            if downgrade_count >= 2:
                grade_level = "极低"
            else:
                grade_level = "低"
        elif grade_level == "低":
            grade_level = "极低"
    
    return f"GRADE {grade_level}级 | {study_type}"

# 优化：重构后的 get_evidence_priority
def get_evidence_priority(paper: dict) -> int:
    """
    根据论文信息获取证据等级优先级数值（用于排序，适配GRADE标准）
    高=4，中=3，低=2，极低=1
    """
    title = paper.get('title', '').lower()
    abstract = paper.get('abstract', '').lower()
    title_abs = title + " " + abstract
    
    # 初始优先级
    _, _, priority = _get_initial_grade_info(title_abs)
    
    # 计算降级次数
    downgrade_count = _get_downgrade_count(paper)
    
    # 根据降级因素调整优先级
    if downgrade_count > 0:
        if priority == 4:  # 原高等级
            priority = 2 if downgrade_count >= 2 else 3
        elif priority == 3:  # 原中等级
            priority = 1 if downgrade_count >= 2 else 2
        elif priority == 2:  # 原低等级
            priority = 1
    
    return priority

# 保持不变（仅替换常量）
def filter_sensitive(query: str) -> bool:
    """
    检查查询是否包含敏感关键词
    """
    sensitive_keywords = [
        '堕胎', '人工流产', '自杀', '自残', '戒毒',
        'abortion', 'suicide', 'self-medication'
    ]
    query_lower = query.lower()
    for kw in sensitive_keywords:
        if kw in query_lower:
            return True
    return False

# 优化：使用常量
def get_evidence_score(paper: dict, level_priority: int) -> int:
    """
    计算证据质量分数（0-100，用于排序加权）
    计算规则：
    - 基础分：GRADE高=80，中=60，低=40，极低=20
    - 年份加分：近3年+15，近5年+10，近10年+5，10年以上不加分
    - 最终分数限制在0-100之间
    """
    # 基础分根据优先级
    base_scores = {
        4: GRADE_CONFIG['high']['base_score'],
        3: GRADE_CONFIG['medium']['base_score'],
        2: GRADE_CONFIG['low']['base_score'],
        1: GRADE_CONFIG['very_low']['base_score']
    }
    base_score = base_scores.get(level_priority, GRADE_CONFIG['default']['base_score'])

    # 年份加分
    year = paper.get('year', 0) or 0
    years_ago = CURRENT_YEAR - year

    if years_ago <= 3:
        year_bonus = 15
    elif years_ago <= 5:
        year_bonus = 10
    elif years_ago <= 10:
        year_bonus = 5
    else:
        year_bonus = 0

    # 最终分数（限制范围）
    final_score = base_score + year_bonus
    return max(0, min(100, final_score))