"""
证据处理工具函数（改进版）
"""

import re

def get_evidence_level(paper: dict) -> str:
    """
    根据论文信息判断证据等级
    """
    title_abs = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()
    year = paper.get('year', 2024)

    # 优先级匹配
    if re.search(r'systematic review|meta-analysis', title_abs):
        level = "⭐⭐⭐ 系统综述/Meta分析"
    elif re.search(r'guideline|consensus|practice guideline', title_abs):
        level = "⭐⭐⭐ 临床指南/共识"
    elif re.search(r'randomized controlled trial|rct', title_abs):
        level = "⭐⭐ 随机对照试验"
    elif re.search(r'prospective cohort|cohort study', title_abs):
        level = "⭐⭐ 前瞻性队列研究"
    elif re.search(r'case-control', title_abs):
        level = "⭐⭐ 病例对照研究"
    elif re.search(r'cross-sectional', title_abs):
        level = "⭐ 横断面研究"
    elif re.search(r'case report|case series', title_abs):
        level = "⭐ 病例报告/病例系列"
    else:
        level = "⭐ 其他研究"

    if year < 2015:
        level += " ⚠️ 时效性较旧"
    return level

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

def get_evidence_priority(level_str: str) -> int:
    """获取证据等级优先级数值（用于排序）"""
    if '系统综述' in level_str or '临床指南' in level_str:
        return 3
    elif '随机对照试验' in level_str or '前瞻性队列' in level_str or '病例对照' in level_str:
        return 2
    else:
        return 1