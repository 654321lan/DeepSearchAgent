"""
学术研究节点（优化版）
"""

import json
import re
import time
from typing import List, Dict, Any

from src.llms.zhipu import ZhipuLLM
from src.tools.openalex_search import OpenAlexSearch
from src.utils.evidence import get_evidence_level, filter_sensitive, get_evidence_priority
from src.prompts.academic_prompts import (
    OPENALEX_QUERY_PROMPT,
    BATCH_EXTRACT_PROMPT,
    SUMMARIZE_PROMPT
)


class AcademicNode:
    def __init__(self, llm_client: ZhipuLLM):
        self.llm = llm_client
        self.search_tool = OpenAlexSearch()

    def _call_llm(self, user_prompt: str, system_prompt: str = "", max_retries: int = 2) -> str:
        """调用 LLM 并增加重试机制"""
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(system_prompt, user_prompt)
                time.sleep(1)  # 每次成功调用后等待1秒，避免触发限流
                return response.strip()
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"LLM 调用失败，{wait}秒后重试... 错误: {e}")
                    time.sleep(wait)
                else:
                    raise
        return ""

    def _filter_relevant_papers(self, papers: List[Dict], query: str, threshold: float = 0.6) -> List[Dict]:
        """使用 LLM 评估论文与查询的相关性，返回高分论文"""
        if not papers:
            return []
        items_text = "\n".join([
            f"标题：{p['title']}\n摘要：{p['abstract'][:300]}"
            for p in papers
        ])
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
            return filtered if filtered else papers[:3]
        except Exception as e:
            print(f"相关性评估失败: {e}，返回全部论文")
            return papers

    def run(self, query: str) -> str:
        try:
            # 敏感词过滤
            if filter_sensitive(query):
                return "⚠️ 检测到敏感内容，无法提供相关学术信息。"

            # 1. 生成英文关键词
            keywords_prompt = OPENALEX_QUERY_PROMPT.format(question=query)
            keywords = self._call_llm(keywords_prompt)
            time.sleep(1)
            if not keywords:
                keywords = "health"

            # 2. 搜索论文（获取较多候选，用于后续过滤）
            papers = self.search_tool.search(keywords, max_results=3)
            if not papers:
                return "未找到相关学术论文，请尝试其他关键词。"

            # 3. 相关性过滤
            #papers = self._filter_relevant_papers(papers, query, threshold=0.6)

            # 4. 添加证据等级并排序
            for p in papers:
                p['evidence_level'] = get_evidence_level(p)
            papers.sort(key=lambda x: (-get_evidence_priority(x['evidence_level']), -x.get('year', 0)))

            # 5. 批量提取关键结论
            items_text = "\n".join([
                f"标题：{p['title']}\n摘要：{p['abstract'][:400]}"
                for p in papers[:5]
            ])
            batch_prompt = BATCH_EXTRACT_PROMPT.format(papers=items_text)
            response = self._call_llm(batch_prompt)
            time.sleep(1)

            # 清理 JSON 响应
            response = re.sub(r'```json\s*|\s*```', '', response).strip()
            try:
                findings = json.loads(response)
                if isinstance(findings, list):
                    title_to_finding = {}
                    for item in findings:
                        if isinstance(item, dict):
                            title_to_finding[item.get('title', '')] = item.get('key_finding', '')
                    for p in papers:
                        p['key_finding'] = title_to_finding.get(p['title'], '未提取到关键发现')
                else:
                    raise ValueError
            except Exception as e:
                print(f"提取关键发现失败: {e}")
                for p in papers:
                    p['key_finding'] = "关键发现解析失败"

            # 6. 生成 Markdown 表格
            table = "| 标题 | 年份 | 证据等级 | 关键结论 |\n|------|------|----------|----------|\n"
            for p in papers[:5]:
                title_short = p['title'][:50] + ('...' if len(p['title']) > 50 else '')
                year = p['year']
                level = p['evidence_level']
                finding = p['key_finding'][:50] + ('...' if len(p['key_finding']) > 50 else '')
                table += f"| {title_short} | {year} | {level} | {finding} |\n"

            # 7. 生成综合回答
            summarize_prompt = SUMMARIZE_PROMPT.format(evidence_table=table)
            summary = self._call_llm(summarize_prompt)

            # 8. 免责声明
            disclaimer = "\n\n---\n⚠️ **免责声明**：本工具仅提供学术文献参考，不构成医疗建议。具体诊疗请咨询专业医生。"
            return f"{table}\n\n{summary}{disclaimer}"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"⚠️ 处理过程中发生错误：{str(e)}。请稍后重试或尝试其他查询。"