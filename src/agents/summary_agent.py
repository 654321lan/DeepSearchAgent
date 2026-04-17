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

    def _call_llm(self, user_prompt: str, system_prompt: str = "", max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(system_prompt, user_prompt)
                # 增加延迟，避免速率限制
                time.sleep(2 + attempt)  # 逐步增加延迟：2秒、3秒、4秒
                return response.strip()
            except Exception as e:
                error_msg = str(e)
                
                # 检查是否为速率限制错误
                if "429" in error_msg or "速率限制" in error_msg or "rate limit" in error_msg.lower():
                    wait_time = 10 * (attempt + 1)  # 速率限制时等待更长时间：10秒、20秒、30秒
                    print(f"⚠️ 速率限制错误，等待{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                elif attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"LLM 调用失败，{wait_time}秒后重试... 错误: {error_msg}")
                    time.sleep(wait_time)
                else:
                    print(f"❌ LLM 调用最终失败: {error_msg}")
                    raise
        return ""

    def _extract_key_findings(self, papers: list) -> list:
        """批量提取关键结论（优化版，减少API调用）"""
        if not papers:
            return papers

        # 为每篇论文设置默认的关键发现
        for p in papers:
            # 从标题和摘要中提取简化的关键发现（避免过度依赖LLM）
            title = p.get('title', '')
            abstract = p.get('abstract', '')
            
            # 简单的关键词提取作为基础关键发现
            if title and abstract:
                # 从标题和摘要前100字中提取关键信息
                text_snippet = f"{title} {abstract[:100]}"
                p['key_finding'] = text_snippet[:80] + "..." if len(text_snippet) > 80 else text_snippet
            else:
                p['key_finding'] = "基于文献证据"

        # 仅对前3篇高质量论文使用LLM提取详细关键发现
        high_quality_papers = [p for p in papers if p.get('evidence_priority', 0) >= 3][:3]
        
        if high_quality_papers:
            try:
                items_text = "\n".join([f"标题：{p['title']}\n摘要：{p.get('abstract', '')[:300]}" for p in high_quality_papers])
                batch_prompt = BATCH_EXTRACT_PROMPT.format(papers=items_text)
                response = self._call_llm(batch_prompt)
                
                if response and len(response.strip()) > 10:
                    response = re.sub(r'```json\s*|\s*```', '', response).strip()
                    try:
                        findings = json.loads(response)
                        if isinstance(findings, list):
                            title_to_finding = {item.get('title', ''): item.get('key_finding', '') for item in findings if isinstance(item, dict)}
                            for p in high_quality_papers:
                                if p['title'] in title_to_finding:
                                    p['key_finding'] = title_to_finding[p['title']]
                    except Exception as e:
                        print(f"关键发现解析失败，使用默认值: {e}")
                else:
                    print("LLM返回空响应，使用默认关键发现")
            except Exception as e:
                print(f"提取关键发现失败，使用默认值: {e}")

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
        summary = self._call_llm(summarize_prompt)
        
        # 调试信息：检查总结内容
        if not summary or len(summary.strip()) < 50:
            print(f"警告：总结内容过短或为空，长度: {len(summary)}")
            # 生成一个兜底的总结
            summary = """## 核心结论
基于现有文献证据，建议咨询专业医生获取个性化诊疗方案。

## 具体循证建议
请结合临床实际情况制定个体化治疗方案。

## 证据来源
详见上方文献表格。"""
        
        return summary

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
        final_report = f"# 文献证据表格\n\n{table}\n\n# 综合总结\n\n{summary}{disclaimer}"

        return {
            'summary': final_report,
            'papers': papers_with_findings,
            'status': 'success',
            'message': '总结生成完成'
        }