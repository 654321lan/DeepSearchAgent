"""
学术研究相关的提示词模板（优化版）
"""

OPENALEX_QUERY_PROMPT = """用户问题：{question}

请生成一个精准的学术搜索查询，用于 OpenAlex。要求：
- 严格保留用户问题中的核心实体（如"游泳"），绝对不要泛化为"运动"等上位词
- 用同义词扩展（OR连接），但必须保留原词
- 追加研究类型限定：(systematic review OR meta-analysis OR randomized controlled trial OR guideline)
- 查询应直接针对用户问题，避免引入任何无关概念（如不要将"心脏"替换成"心血管疾病"泛化）
- 只输出查询字符串，不要有其他内容。

示例：
用户问题：游泳对心脏的影响
输出：swimming heart
请输出："""

BATCH_EXTRACT_PROMPT = """从给定的论文标题和摘要中提取每篇的核心发现（30字内），输出 JSON 数组格式。

论文列表：
{papers}

输出格式：[{{"title": "论文标题", "key_finding": "核心发现（30字内）"}}]"""

CROSSREF_QUERY_PROMPT = """用户问题：{question}
请生成3-5个简短的英文搜索关键词短语，用逗号分隔，用于学术文献检索。要求：
- 使用英文，每个短语由2-4个关键词组成
- 不要使用 AND/OR 等布尔运算符
- 针对"注意事项"、"安全性"等问题，请使用 safety, risk, guideline 等词
- 例如：心血管疾病患者跑步注意事项 -> cardiovascular disease running, heart disease exercise, cardiac rehabilitation safety, exercise risk assessment, cardiovascular health guidelines
- 只输出关键词短语列表，用逗号分隔，不要有其他内容。

请输出："""

SUMMARIZE_PROMPT = """【循证医学专家prompt】
你是专业的循证医学专家，请基于以下用户问题和文献证据，生成专业、详细、结构化的医学结论。
要求：
1.  必须100%基于提供的文献内容生成结论，所有内容必须有文献支撑
2.  必须提取文献中具体可量化的循证标准（如供能比、摄入量、限制值等）
3.  每一条建议必须在句尾标注对应的文献来源（指南名称、发布年份），优先使用GRADE高级文献
4.  结构清晰，只回答用户的原始问题，不输出无关内容

用户问题：{question}
可用文献：{papers_list}"""