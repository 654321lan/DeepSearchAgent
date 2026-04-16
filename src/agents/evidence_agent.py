from .base_agent import BaseAgent
from src.utils.evidence import get_evidence_level, get_evidence_priority

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

        # 计算综合分数
        for idx, p in enumerate(papers):
            # 相关性分数
            if 'score' in p and p['score']:
                # Crossref 的 score 是 0-100，归一化到 0-1
                relevance = p['score'] / 100.0
            else:
                # OpenAlex 使用位置分数（假设按相关性排序）
                relevance = max(0.1, 1.0 - idx * 0.1)
            # 证据等级优先级（3最高，1最低）
            evidence_level = p.get('evidence_level', '⭐ 其他研究')
            priority = get_evidence_priority(evidence_level)  # 返回 3,2,1
            # 年份归一化（2000-2030）
            year = p.get('year', 0) or 0
            year_norm = min(1.0, (year - 2000) / 30) if year > 2000 else 0
            # 综合分数：相关性0.5，证据等级0.3，年份0.2
            p['combined_score'] = 0.5 * relevance + 0.3 * (priority / 3) + 0.2 * year_norm

        # 按综合分数降序排序
        papers.sort(key=lambda x: -x.get('combined_score', 0))
        papers = papers[:5]  # 取前5篇

        return {
            'papers': papers,
            'status': 'success',
            'message': '证据等级添加和排序完成'
        }