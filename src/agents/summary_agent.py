from .base_agent import BaseAgent
from src.llms.zhipu import ZhipuLLM
from src.prompts.academic_prompts import BATCH_EXTRACT_PROMPT
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

    def _generate_summary(self, query: str, papers: list) -> str:
        """生成综合回答 - 锁死量化强制规则"""
        print(f"\n{'='*60}")
        print(f"【节点6：开始生成总结】用户问题：{query}")
        print(f"【节点6：文献数量】{len(papers)}篇")

        # 构建完整的文献列表，包含标题、摘要、GRADE分级、发布年份
        papers_list = []
        for i, p in enumerate(papers, 1):
            paper_info = f"【文献{i}】\n"
            paper_info += f"标题：{p.get('title', 'N/A')}\n"
            paper_info += f"GRADE分级：{p.get('evidence_level', 'N/A')}\n"
            paper_info += f"发布年份：{p.get('year', 'N/A')}\n"
            paper_info += f"摘要：{p.get('abstract', 'N/A')}"
            papers_list.append(paper_info)

        papers_text = "\n\n===\n\n".join(papers_list)
        print(f"【节点6：文献数据完整性】摘要总字符数：{sum(len(p.get('abstract', '')) for p in papers)}")

        # 锁死的量化强制system prompt
        system_prompt = """你是严格的循证医学证据分析专家。输出必须严格遵守以下铁律：

【铁律1：量化强制 - 绝对禁止违反】
每条结论必须包含具体数值，格式如：
- "150-200分钟/周"
- "30-40kcal/kg/天"
- "<2g/日"
- "收缩压<140mmHg"
- "每周3-5次"

严禁使用的模糊词（发现即判定为违规）：
- 适量、适当、一定量、足够、充分
- 建议咨询医生、具体需因人而异、个体化决策
- 标准化流程、综合措施、参考高质量文献

如文献未提供具体数值，必须明确写："文献未提供具体数值"

【铁律2：来源强制 - 绝对禁止违反】
每句话结尾必须标注：[来源：标题 年份 GRADE X]
示例：
"每周运动150-250分钟可降低心血管风险 [来源：运动与健康指南 2022 GRADE A]"

禁止无来源的结论。

【铁律3：内容强制 - 绝对禁止违反】
- 只回答用户问题，不展开任何无关话题
- 禁止任何形式的通用免责话术
- 如文献证据不足，必须写："现有文献未提供充分量化证据"

【输出格式】
直接输出结论，使用列表形式：
• 结论1 [来源：文献标题 年份 GRADE X]
• 结论2 [来源：文献标题 年份 GRADE X]"""

        user_prompt = f"""【用户问题】
{query}

【可用文献证据】（共{len(papers)}篇）
{papers_text}

请严格遵循上述铁律，基于文献证据生成量化结论："""

        # 打印传入LLM的完整prompt（调试用）
        print(f"\n{'='*60}")
        print("【节点6：传入LLM的完整System Prompt】")
        print(system_prompt)
        print(f"\n{'='*60}")
        print("【节点6：传入LLM的完整User Prompt】")
        print(user_prompt[:500] + "..." if len(user_prompt) > 500 else user_prompt)
        print(f"{'='*60}\n")

        summary = self._call_llm(user_prompt, system_prompt)

        # 调试信息：检查总结内容
        print(f"【节点6：LLM响应长度】{len(summary)}字符")
        print(f"【节点6：LLM响应内容】{summary[:200]}..." if len(summary) > 200 else summary)

        # 检测是否包含被禁止的模糊词
        forbidden_words = ['适量', '适当', '一定量', '建议咨询医生', '因人而异', '标准化流程', '综合措施', '参考高质量文献']
        found_forbidden = [word for word in forbidden_words if word in summary]
        if found_forbidden:
            print(f"⚠️ 警告：总结包含被禁止的模糊词：{found_forbidden}")

        if not summary or len(summary.strip()) < 50:
            print(f"❌ 错误：总结内容过短或为空，长度: {len(summary)}")
            summary = f"⚠️ 现有文献（共{len(papers)}篇）未能提供回答该问题的具体量化证据。建议扩大检索范围或调整问题表述。"

        print(f"{'='*60}\n")
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

        # 生成总结 - 传入完整的papers信息
        summary = self._generate_summary(query, papers_with_findings)

        disclaimer = "\n\n---\n⚠️ **免责声明**：本工具仅提供学术文献参考，不构成医疗建议。具体诊疗请咨询专业医生。"
        final_report = f"# 文献证据表格\n\n{table}\n\n# 综合总结\n\n{summary}{disclaimer}"

        return {
            'summary': final_report,
            'papers': papers_with_findings,
            'status': 'success',
            'message': '总结生成完成'
        }