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
请生成一个简短的自然语言搜索短语，用于 Crossref API。要求：
- 使用英文，只包含核心关键词，不要使用 AND/OR 等布尔运算符
- 针对“注意事项”、“安全性”等问题，请使用 safety, risk, guideline 等词，避免使用 precautions（易匹配不相关领域）
- 例如：心血管疾病患者跑步注意事项 -> cardiovascular disease running safety
- 只输出搜索短语，不要有其他内容。

请输出："""

SUMMARIZE_PROMPT = """用户问题：{question}
以下是相关学术论文的证据表格：
{evidence_table}
请根据这些证据，用中文写一段总结（不超过300字），要求：
1. 按证据等级从高到低分层总结（系统综述/指南优先，然后是随机对照试验，最后是观察性研究）
2. 每段只写一个核心发现，不同发现之间用空行分隔
3. 直接回答用户问题，不要给出医疗建议
4. 末尾注明“根据现有研究”

请输出："""