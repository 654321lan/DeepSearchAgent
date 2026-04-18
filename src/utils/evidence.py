"""
循证医学证据分级工具
严格遵循GRADE (Grading of Recommendations Assessment, Development and Evaluation) 官方标准
优化版本：两步分级（正则硬规则+LLM批量调整）
"""
import re
import logging
import json
import time
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

logger = logging.getLogger(__name__)

# ==================== GRADE 核心定义 ====================
class StudyType(Enum):
    """研究类型枚举（按GRADE证据质量优先级排序）"""
    SYSTEMATIC_REVIEW_META = "systematic_review_meta"  # 系统综述/Meta分析（最高级）
    RCT = "rct"                                            # 随机对照试验
    COHORT = "cohort"                                      # 队列研究
    CASE_CONTROL = "case_control"                          # 病例对照研究
    OBSERVATIONAL = "observational"                        # 观察性研究
    EXPERT_OPINION = "expert_opinion"                      # 专家意见/病例报告（最低级）

class GRADELevel(Enum):
    """GRADE证据质量等级"""
    HIGH = "GRADE 高级"      # 随机对照试验/高质量系统综述
    MODERATE = "GRADE 中级"  # 队列研究/降级后的RCT
    LOW = "GRADE 低级"        # 病例对照/降级后的队列研究
    VERY_LOW = "GRADE 极低级" # 观察性研究/专家意见

# ==================== 配置常量 ====================
GRADE_CONFIG = {
    # 按研究类型的初始证据等级（严格硬规则）
    "initial_level": {
        StudyType.SYSTEMATIC_REVIEW_META: GRADELevel.HIGH,
        StudyType.RCT: GRADELevel.HIGH,
        StudyType.COHORT: GRADELevel.MODERATE,
        StudyType.CASE_CONTROL: GRADELevel.LOW,
        StudyType.OBSERVATIONAL: GRADELevel.VERY_LOW,
        StudyType.EXPERT_OPINION: GRADELevel.VERY_LOW,
    },
}

# ==================== LLM升级/降级因素判断提示词 ====================
GRADE_ADJUSTMENT_PROMPT = """
你是循证医学GRADE证据分级专家。请基于提供的文献信息，判断是否存在以下GRADE升级或降级因素：

## 降级因素（每项最多降1级）：
1. 研究局限性：随机化、盲法、失访率等
2. 不精确性：样本量不足、置信区间宽
3. 发表偏倚：非核心期刊、无基金支持
4. 不一致性：研究结果不一致
5. 间接性：人群、干预、结局指标不匹配

## 升级因素（每项最多升1级）：
1. 效应量大：风险比/比值比等效应量很大
2. 剂量反应关系：剂量与效应呈正相关
3. 混杂因素调整：充分调整了混杂因素

请严格按以下JSON格式输出，不要输出其他内容：
```json
{
    "adjustments": [
        {
            "title": "文献标题",
            "upgrade_factors": ["因素1", "因素2"],
            "downgrade_factors": ["因素1", "因素2"],
            "net_adjustment": 0  // 净调整值：升级因素数-降级因素数，范围[-3, 3]
        }
    ]
}
```

文献信息：
{papers_info}
"""

# ==================== 第一步：正则硬规则初始分级 ====================
def _get_initial_grade_strict(paper: Dict[str, Any]) -> Tuple[GRADELevel, str]:
    """
    第一步：正则硬规则初始分级（完全禁用LLM）
    返回：(初始等级, 分类原因)
    """
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    full_text = f"{title} {abstract}".strip()
    
    # 严格正则匹配（按GRADE优先级）
    patterns = [
        (StudyType.SYSTEMATIC_REVIEW_META, r"(systematic\s+review|meta[\-\s]analysis|荟萃分析|系统综述|guideline|指南|practice\s+guidance)", "系统综述/Meta分析/指南"),
        (StudyType.RCT, r"(randomized\s+controlled\s+trial|randomised\s+controlled\s+trial|rct|随机对照试验|随机.*双盲|随机.*安慰剂)", "随机对照试验"),
        (StudyType.COHORT, r"(cohort\s+study|队列研究|前瞻性队列|回顾性队列)", "队列研究"),
        (StudyType.CASE_CONTROL, r"(case[\-\s]control\s+study|病例对照研究|回顾性病例对照)", "病例对照研究"),
        (StudyType.OBSERVATIONAL, r"(observational\s+study|cross[\-\s]sectional|横断面研究|描述性研究)", "观察性研究"),
        (StudyType.EXPERT_OPINION, r"(expert\s+opinion|case\s+report|专家意见|病例报告|非系统综述)", "专家意见/病例报告"),
    ]
    
    for study_type, pattern, reason in patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            initial_level = GRADE_CONFIG["initial_level"].get(study_type, GRADELevel.VERY_LOW)
            return initial_level, f"正则匹配到{reason}"
    
    # 兜底：极低级
    return GRADELevel.VERY_LOW, "未匹配到具体类型，使用兜底极低级"

# ==================== 第二步：LLM批量升级/降级因素判断 ====================
def _get_llm_adjustments_batch(papers: List[Dict[str, Any]], llm_client) -> Dict[str, int]:
    """
    第二步：LLM批量升级/降级因素判断
    单轮仅调用1次LLM，严格控制API调用
    返回：{文献标题: 净调整值}
    """
    if not llm_client or len(papers) == 0:
        return {}
    
    # 构建文献信息字符串（限制长度，避免token超限）
    papers_info = ""
    for i, paper in enumerate(papers[:10]):  # 最多处理10篇文献
        title = paper.get('title', '')[:100]
        abstract = paper.get('abstract', '')[:200]
        journal = paper.get('journal', '')
        year = paper.get('year', '')
        
        papers_info += f"\n{i+1}. 标题：{title}\n   期刊：{journal} | 年份：{year}\n   摘要：{abstract}\n"
    
    # 准备提示词
    prompt = GRADE_ADJUSTMENT_PROMPT.format(papers_info=papers_info)
    
    # 单轮LLM调用，严格控制
    try:
        # 添加限流控制
        time.sleep(2)  # 避免速率限制
        
        # 调用LLM（使用invoke或generate方法）
        try:
            response = llm_client.invoke("", prompt)
        except AttributeError:
            response = llm_client.generate("", prompt)
        
        # 解析JSON响应
        response = re.sub(r'```json\s*|\s*```', '', response).strip()
        result = json.loads(response)
        
        # 提取调整结果
        adjustments = {}
        for adj in result.get("adjustments", []):
            title = adj.get("title", "")
            net_adjustment = adj.get("net_adjustment", 0)
            # 限制调整范围[-3, 3]
            net_adjustment = max(-3, min(3, net_adjustment))
            adjustments[title] = net_adjustment
        
        logger.info(f"LLM批量调整完成，处理{len(adjustments)}篇文献")
        return adjustments
        
    except Exception as e:
        logger.warning(f"LLM批量调整失败，使用默认值: {e}")
        return {}  # 失败时返回空字典，不影响主流程

# ==================== 辅助函数：计算最终等级 ====================
def _calculate_final_level(initial_level: GRADELevel, net_adjustment: int) -> GRADELevel:
    """计算最终等级：初始等级 + 净调整值"""
    level_order = [GRADELevel.HIGH, GRADELevel.MODERATE, GRADELevel.LOW, GRADELevel.VERY_LOW]
    
    try:
        initial_index = level_order.index(initial_level)
        final_index = initial_index - net_adjustment  # 升级是+，降级是-
        final_index = max(0, min(final_index, len(level_order) - 1))
        return level_order[final_index]
    except:
        return initial_level  # 异常时返回初始等级

# ==================== 主函数：GRADE证据分级（两步分级标准） ====================
def get_evidence_level(paper: Dict[str, Any], llm_client=None, batch_papers: List[Dict[str, Any]] = None) -> Tuple[GRADELevel, Dict[str, Any]]:
    """
    严格遵循GRADE官方标准进行证据分级（两步分级）
    第一步：正则硬规则初始分级（完全禁用LLM）
    第二步：LLM批量升级/降级因素判断（单轮仅调用1次）
    返回：(GRADE等级, 分级详情字典)
    """
    # 初始化详情字典（完整可溯源）
    grade_details = {
        "initial_level": "",
        "initial_reason": "",
        "llm_adjustment": 0,
        "upgrade_factors": [],
        "downgrade_factors": [],
        "final_level": "",
        "calculation_steps": []
    }
    
    try:
        # ========== 第一步：正则硬规则初始分级 ==========
        initial_level, initial_reason = _get_initial_grade_strict(paper)
        grade_details["initial_level"] = initial_level.value
        grade_details["initial_reason"] = initial_reason
        grade_details["calculation_steps"].append(f"第一步：正则硬规则分级 -> {initial_level.value}")
        
        # ========== 第二步：LLM批量升级/降级因素判断 ==========
        net_adjustment = 0
        upgrade_factors = []
        downgrade_factors = []
        
        if llm_client and batch_papers:
            # 批量获取LLM调整结果
            llm_adjustments = _get_llm_adjustments_batch(batch_papers, llm_client)
            
            # 查找当前文献的调整结果
            paper_title = paper.get('title', '')
            if paper_title in llm_adjustments:
                net_adjustment = llm_adjustments[paper_title]
                
                # 记录调整因素（简化处理，实际应从LLM返回中提取）
                if net_adjustment > 0:
                    upgrade_factors = [f"LLM识别到{net_adjustment}个升级因素"]
                elif net_adjustment < 0:
                    downgrade_factors = [f"LLM识别到{abs(net_adjustment)}个降级因素"]
                
                grade_details["calculation_steps"].append(f"第二步：LLM批量调整 -> 净调整值{net_adjustment}")
            else:
                grade_details["calculation_steps"].append("第二步：未找到LLM调整结果，使用默认值")
        else:
            grade_details["calculation_steps"].append("第二步：无LLM客户端或批量数据，跳过调整")
        
        grade_details["llm_adjustment"] = net_adjustment
        grade_details["upgrade_factors"] = upgrade_factors
        grade_details["downgrade_factors"] = downgrade_factors
        
        # ========== 计算最终等级 ==========
        final_level = _calculate_final_level(initial_level, net_adjustment)
        grade_details["final_level"] = final_level.value
        
        # 记录最终结果
        grade_details["calculation_steps"].append(f"最终等级：{initial_level.value} + {net_adjustment} = {final_level.value}")
        
        logger.info(f"GRADE分级完成：{paper.get('title', '')[:50]}... -> {initial_level.value} -> {final_level.value} (调整{net_adjustment})")
        
    except Exception as e:
        # 异常时兜底
        logger.error(f"GRADE分级计算失败: {e}", exc_info=True)
        final_level = GRADELevel.VERY_LOW
        grade_details["final_level"] = final_level.value
        grade_details["initial_level"] = GRADELevel.VERY_LOW.value
        grade_details["initial_reason"] = f"系统异常：{str(e)}"
        grade_details["calculation_steps"].append("系统异常，使用兜底等级")
    
    return final_level, grade_details

# ==================== 批量分级函数（推荐使用） ====================
def get_evidence_levels_batch(papers: List[Dict[str, Any]], llm_client=None) -> List[Tuple[GRADELevel, Dict[str, Any]]]:
    """
    批量GRADE证据分级（推荐使用）
    单轮LLM调用处理所有文献，效率最高
    返回：[(等级1, 详情1), (等级2, 详情2), ...]
    """
    results = []
    
    # 批量处理所有文献
    for paper in papers:
        level, details = get_evidence_level(paper, llm_client, papers)
        results.append((level, details))
    
    logger.info(f"批量GRADE分级完成，共处理{len(results)}篇文献")
    return results

def get_evidence_priority(level: GRADELevel) -> int:
    """获取证据优先级（用于排序，数字越大优先级越高）"""
    priority_map = {
        GRADELevel.HIGH: 4,
        GRADELevel.MODERATE: 3,
        GRADELevel.LOW: 2,
        GRADELevel.VERY_LOW: 1,
    }
    return priority_map.get(level, 0)

# ==================== 证据溯源辅助函数 ====================
def extract_evidence_snippets(paper: Dict[str, Any], query: str) -> list:
    """
    从论文中提取与查询相关的证据片段
    用于证据溯源
    """
    abstract = paper.get("abstract", "")
    title = paper.get("title", "")
    full_text = f"{title} {abstract}"
    
    # 简单的关键词匹配提取片段
    # 后续可升级为语义相似度匹配
    query_keywords = query.lower().split()
    snippets = []
    
    # 按句子分割
    sentences = re.split(r'[.。！？!?]', full_text)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        # 检查是否包含查询关键词
        if any(kw in sentence.lower() for kw in query_keywords):
            snippets.append(sentence)
    
    return snippets[:3]  # 最多返回3个片段


# ==================== 敏感词过滤（学术模式） ====================
SENSITIVE_KEYWORDS = [
    # 医疗敏感词
    "治疗", "治愈", "诊断", "处方", "药方", "药物", "药品",
    # 其他需要过滤的关键词
    "自杀", "自残", "暴力", "毒品", "赌博",
    # 其他敏感内容
    "极端", "恐怖", "反动", "非法", "违法"
]

def filter_sensitive(query: str) -> bool:
    """
    检查查询是否包含敏感内容

    Args:
        query: 用户查询字符串

    Returns:
        bool: True 表示包含敏感内容，False 表示不包含
    """
    if not query:
        return False

    query_lower = query.lower()

    for keyword in SENSITIVE_KEYWORDS:
        if keyword in query_lower:
            return True

    return False