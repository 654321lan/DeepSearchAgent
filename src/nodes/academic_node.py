"""
学术研究节点（优化版，支持 Crossref + OpenAlex 双引擎，优先使用 Crossref）
"""

import json
import re
import time
from typing import List, Dict, Any

from src.llms.zhipu import ZhipuLLM
from src.tools.crossref_search import CrossrefSearch
from src.tools.openalex_search import OpenAlexSearch
from src.utils.evidence import get_evidence_level, filter_sensitive, get_evidence_priority
from src.prompts.academic_prompts import (
    OPENALEX_QUERY_PROMPT,
    CROSSREF_QUERY_PROMPT,
    BATCH_EXTRACT_PROMPT,
    SUMMARIZE_PROMPT
)


class AcademicNode:
    def __init__(self, llm_client: ZhipuLLM, config=None):
        self.llm = llm_client
        self.config = config
        self.crossref_search = CrossrefSearch()
        self.openalex_search = OpenAlexSearch()
        self.use_crossref = True
        if config:
            self.use_crossref = getattr(config, 'use_crossref', True)

    def _call_llm(self, user_prompt: str, system_prompt: str = "", max_retries: int = 2) -> str:
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(system_prompt, user_prompt)
                time.sleep(1)
                return response.strip()
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"LLM 调用失败，{wait}秒后重试... 错误: {e}")
                    time.sleep(wait)
                else:
                    raise
        return ""

    def _filter_relevant_papers(self, papers: List[Dict], query: str, threshold: float = 0.5) -> List[Dict]:
        """使用 LLM 评估论文与查询的相关性，返回高分论文（阈值0.5）"""
        if not papers:
            return []
        items_text = "\n".join([f"标题：{p['title']}\n摘要：{p.get('abstract', '')[:300]}" for p in papers])
        prompt = f"""用户问题：{query}
请评估以下论文与用户问题的相关性，为每篇输出一个 0-1 之间的分数（仅分数，不要解释）。格式：每行 "标题：分数"

{items_text}
"""
        try:
            response = self._call_llm(prompt)
            lines = response.strip().split('\n')
            scores = {}
            for line in lines:
                if '：' in line:
                    title, score_str = line.split('：', 1)
                    title = title.strip().strip('*').strip()
                    try:
                        scores[title] = float(score_str.strip())
                    except:
                        pass
            filtered = [p for p in papers if scores.get(p['title'], 0) >= threshold]
            return filtered if filtered else papers[:3]  # 全过滤则保留前3篇
        except Exception as e:
            print(f"相关性评估失败: {e}，返回全部论文")
            return papers

    def run(self, query: str) -> str:
        try:
            if filter_sensitive(query):
                return "⚠️ 检测到敏感内容，无法提供相关学术信息。"

            # 1. 生成关键词
            if self.use_crossref:
                keywords_prompt = CROSSREF_QUERY_PROMPT.format(question=query)
            else:
                keywords_prompt = OPENALEX_QUERY_PROMPT.format(question=query)
            keywords = self._call_llm(keywords_prompt)
            print(f"生成的搜索词: {keywords}")
            time.sleep(1)
            if not keywords:
                keywords = "health"

            # 2. 搜索论文（增加到10篇，备份原始结果）
            papers = []
            original_papers = []
            if self.use_crossref:
                papers = self.crossref_search.search(keywords, max_results=10)
                original_papers = papers.copy()
            if not papers:
                papers = self.openalex_search.search(keywords, max_results=10)
                original_papers = papers.copy()

            if not papers:
                return "未找到相关学术论文，请尝试其他关键词。"

            # 3. 相关性过滤（启用，阈值0.5）
            papers = self._filter_relevant_papers(papers, query, threshold=0.5)
            if not papers:
                papers = original_papers[:3]  # 后备：使用原始前3篇

            # 4. 证据等级和排序
            for p in papers:
                p['evidence_level'] = get_evidence_level(p)
                year = p.get('year', 0)
                if year is None:
                    year = 0
                year_norm = min(1.0, (year - 2000) / 30) if year > 2000 else 0
                priority_norm = get_evidence_priority(p['evidence_level']) / 3
                p['combined_score'] = 0.6 * p.get('relevance_score', 0.5) + 0.2 * year_norm + 0.2 * priority_norm
            papers.sort(key=lambda x: -x.get('combined_score', 0))

            # 5. 强制所有论文使用 LLM 批量提取关键结论
            for p in papers:
                p['key_finding'] = ""  # 清空，确保进入批量提取
            missing = papers
            if missing:
                items_text = "\n".join([f"标题：{p['title']}\n摘要：{p.get('abstract', '')[:400]}" for p in missing[:5]])
                batch_prompt = BATCH_EXTRACT_PROMPT.format(papers=items_text)
                response = self._call_llm(batch_prompt)
                time.sleep(1)
                response = re.sub(r'```json\s*|\s*```', '', response).strip()
                try:
                    findings = json.loads(response)
                    if isinstance(findings, list):
                        title_to_finding = {item.get('title', ''): item.get('key_finding', '') for item in findings if isinstance(item, dict)}
                        for p in missing:
                            p['key_finding'] = title_to_finding.get(p['title'], '未提取到关键发现')
                except Exception as e:
                    print(f"提取关键发现失败: {e}")
                    for p in missing:
                        p['key_finding'] = "关键发现解析失败"

            # 6. 生成表格
            table = "| 标题 | 年份 | 证据等级 | 关键结论 |\n|------|------|----------|----------|\n"
            for p in papers[:5]:
                title_short = p['title'][:50] + ('...' if len(p['title']) > 50 else '')
                year = p['year']
                level = p['evidence_level']
                finding = p.get('key_finding', '')[:50] + ('...' if len(p.get('key_finding', '')) > 50 else '')
                table += f"| {title_short} | {year} | {level} | {finding} |\n"

            # 7. 综合回答
            summarize_prompt = SUMMARIZE_PROMPT.format(question=query, evidence_table=table)
            summary = self._call_llm(summarize_prompt)

            disclaimer = "\n\n---\n⚠️ **免责声明**：本工具仅提供学术文献参考，不构成医疗建议。具体诊疗请咨询专业医生。"
            return f"{table}\n\n{summary}{disclaimer}"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"⚠️ 处理过程中发生错误：{str(e)}。请稍后重试或尝试其他查询。"