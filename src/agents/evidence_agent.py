from .base_agent import BaseAgent
from src.utils.evidence import get_evidence_level, get_evidence_priority, get_evidence_score  # 新增导入

class EvidenceAgent(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name)

    def process(self, input_data: dict) -> dict:
        papers = input_data.get('papers', [])
        if not papers:
            return {'papers': [], 'status': 'error', 'message': '论文列表为空'}

        # 为每篇论文添加证据等级
        for p in papers:
            p['evidence_level'] = get_evidence_level(p)
            # 获取证据优先级（修复原逻辑错误）
            p['evidence_priority'] = get_evidence_priority(p)
            # 计算证据质量分数
            p['evidence_score'] = get_evidence_score(p, p['evidence_priority'])

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