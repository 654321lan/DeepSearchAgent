from .base_agent import BaseAgent
from src.utils.evidence import get_evidence_level, get_evidence_priority

def get_evidence_score(paper: dict, priority: int) -> int:
    """计算证据质量分数（综合评分 0-100）"""
    # 基础分：基于优先级 (1-4) -> (25-100)
    base_score = priority * 25

    # 调整项1：期刊质量（如果有期刊信息）
    journal = paper.get('journal', '').lower()
    core_journals = ['lancet', 'nejm', 'jama', 'bmj', 'nature', 'science', 'cell', 'circulation', 'diabetes care']
    if any(cj in journal for cj in core_journals):
        base_score = min(100, base_score + 10)

    # 调整项2：年份（越新越好）
    year = paper.get('year', 0) or 0
    if year >= 2024:
        base_score = min(100, base_score + 5)
    elif year >= 2020:
        base_score = min(100, base_score + 3)

    # 调整项3：引用数（如果有）
    citations = paper.get('cited_by_count', 0) or 0
    if citations >= 100:
        base_score = min(100, base_score + 5)
    elif citations >= 50:
        base_score = min(100, base_score + 3)

    return min(100, max(0, base_score))


class EvidenceAgent(BaseAgent):
    def __init__(self, name: str, llm=None):
        super().__init__(name)
        self.llm = llm

    def process(self, input_data: dict) -> dict:
        papers = input_data.get('papers', [])
        if not papers:
            return {'papers': [], 'status': 'error', 'message': '论文列表为空'}

        # 为每篇论文添加证据等级
        for p in papers:
            try:
                # 修复：get_evidence_level 返回元组 (level, details)，需要解构
                level, details = get_evidence_level(p)
                p['evidence_level'] = level.value  # 存储字符串值
                # 只在details不为空时更新grade_details
                if details and details.get('study_type'):
                    p['grade_details'] = details
                # 添加证据片段（从论文标题和摘要中提取）
                snippets = []
                title = p.get('title', '')
                if title and title.strip():
                    snippets.append(f"标题：{title}")
                abstract = p.get('abstract', '')
                if abstract and abstract.strip():
                    # 从摘要中提取前150个字符作为证据片段
                    abstract_snippet = abstract[:150] + ('...' if len(abstract) > 150 else '')
                    snippets.append(f"摘要：{abstract_snippet}")
                p['evidence_snippets'] = snippets if snippets else ["无可用证据片段（无标题或摘要）"]
                # 获取证据优先级
                p['evidence_priority'] = get_evidence_priority(level)
                # 计算证据质量分数
                p['evidence_score'] = get_evidence_score(p, p['evidence_priority'])
            except Exception as e:
                import logging
                logging.error(f"处理论文时出错: {p.get('title', '未知标题')}, 错误: {e}")
                # 确保即使出错也有默认值
                if 'evidence_level' not in p:
                    p['evidence_level'] = 'GRADE 极低级'
                if 'evidence_snippets' not in p:
                    p['evidence_snippets'] = ["无可用证据片段"]
                if 'evidence_priority' not in p:
                    p['evidence_priority'] = 1
                if 'evidence_score' not in p:
                    p['evidence_score'] = 20

        # 计算综合分数
        for idx, p in enumerate(papers):
            # 相关性分数（兼容 Crossref 和 OpenAlex 数据源）
            if 'relevance_score' in p and p['relevance_score']:
                # Crossref 已归一化到 0-1
                relevance = p['relevance_score']
            elif 'score' in p and p['score']:
                # 兼容其他数据源（如 OpenAlex 可能是 0-100）
                relevance = p['score'] / 100.0
            else:
                # 按位置计算相关性（排序后）
                relevance = max(0.1, 1.0 - idx * 0.1)
            
            # 证据等级优先级（修正：使用已计算的 priority，而非从字符串解析）
            priority = p.get('evidence_priority', 1)  # 4=高,3=中,2=低,1=极低
            priority_norm = priority / 4  # 归一化到 0-1（原用3是错误的，因为priority是4/3/2/1）
            
            # 年份归一化（优化：使用当前年份动态计算，而非固定2000-2030）
            year = p.get('year', 0) or 0
            current_year = 2026  # 可抽成常量
            if year >= 2000 and year <= current_year:
                year_norm = (year - 2000) / (current_year - 2000)  # 动态区间
            else:
                year_norm = 0.0
            
            # 综合分数：调整权重（相关性0.4，证据质量0.4，年份0.2）
            # 优化：使用证据质量分数（0-100）归一化后参与计算，更精准
            evidence_score_norm = p.get('evidence_score', 20) / 100.0
            p['combined_score'] = (
                0.4 * relevance +       # 相关性权重
                0.4 * evidence_score_norm +  # 证据质量权重（替代原优先级）
                0.2 * year_norm         # 年份权重
            )

        # 按综合分数降序排序
        papers.sort(key=lambda x: -x.get('combined_score', 0))
        papers = papers[:5]  # 取前5篇

        return {
            'papers': papers,
            'status': 'success',
            'message': '证据等级添加和排序完成'
        }