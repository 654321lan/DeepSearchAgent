from .base_agent import BaseAgent
from src.llms.zhipu import ZhipuLLM
from src.prompts.academic_prompts import BATCH_EXTRACT_PROMPT, SUMMARIZE_PROMPT
import re
import json
import time

class SummaryAgent(BaseAgent):
    def __init__(self, name: str, llm: ZhipuLLM):
        super().__init__(name)
        self.llm = llm

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

    def _extract_key_findings(self, papers: list) -> list:
        """批量提取关键结论"""
        if not papers:
            return papers

        for p in papers:
            p['key_finding'] = ""

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

        return papers

    def _generate_table(self, papers: list) -> str:
        """生成论文表格"""
        table = "| 标题 | 年份 | 证据等级 | 关键结论 |\n|------|------|----------|----------|\n"
        for p in papers:
            title_short = p['title'][:50] + ('...' if len(p['title']) > 50 else '')
            year = p['year']
            level = p['evidence_level']
            finding = p.get('key_finding', '')[:50] + ('...' if len(p.get('key_finding', '')) > 50 else '')
            table += f"| {title_short} | {year} | {level} | {finding} |\n"
        return table

    def _generate_summary(self, query: str, table: str) -> str:
        """生成综合回答"""
        summarize_prompt = SUMMARIZE_PROMPT.format(question=query, evidence_table=table)
        return self._call_llm(summarize_prompt)

    def process(self, input_data: dict) -> dict:
        query = input_data.get('query', '')
        papers = input_data.get('papers', [])

        if not query or not papers:
            return {'summary': '', 'papers': [], 'status': 'error', 'message': '查询或论文列表为空'}

        # 提取关键结论
        papers_with_findings = self._extract_key_findings(papers)

        # 生成表格
        table = self._generate_table(papers_with_findings)

        # 生成总结
        summary = self._generate_summary(query, table)

        disclaimer = "\n\n---\n⚠️ **免责声明**：本工具仅提供学术文献参考，不构成医疗建议。具体诊疗请咨询专业医生。"
        final_report = f"{table}\n\n{summary}{disclaimer}"

        return {
            'summary': final_report,
            'papers': papers_with_findings,
            'status': 'success',
            'message': '总结生成完成'
        }