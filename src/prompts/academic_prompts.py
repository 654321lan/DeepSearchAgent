"""
学术研究相关的提示词模板（优化版）
"""

OPENALEX_QUERY_PROMPT = """你是一个学术搜索专家。用户问题：{question}

请生成一个精准的学术搜索查询，用于 OpenAlex 数据库。要求：
- 使用英文，核心概念用同义词扩展（用 OR 连接）
- 如有必要，追加研究类型限定：(systematic review OR meta-analysis OR guideline OR randomized controlled trial)
- 只输出查询字符串，不要有其他内容。

示例1：
用户问题：高血压患者饮水建议
输出：("hypertension" OR "high blood pressure") AND ("water intake" OR "fluid consumption") AND (systematic review OR guideline)

示例2：
用户问题：心血管疾病患者久坐影响
输出：("cardiovascular disease" OR "heart disease") AND sedentary AND (systematic review OR meta-analysis)

请输出："""

BATCH_EXTRACT_PROMPT = """从给定的论文标题和摘要中提取每篇的核心发现（30字内），输出 JSON 数组格式。

论文列表：
{papers}

输出格式：[{{"title": "论文标题", "key_finding": "核心发现（30字内）"}}]"""

SUMMARIZE_PROMPT = """根据表格中的证据生成不超过 200 字的中文综合回答，末尾注明"根据现有研究"。

证据表格：
{evidence_table}

综合回答："""