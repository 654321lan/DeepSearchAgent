"""
循证医学证据分级工具
严格遵循GRADE (Grading of Recommendations Assessment, Development and Evaluation) 官方标准
优化版本：正则硬规则全链路溯源分级
"""
import re
import logging
from typing import Dict, Any, Tuple, List
from enum import Enum
from dataclasses import dataclass, asdict

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

@dataclass
class GRADEAdjustmentFactor:
    """GRADE升降级因素"""
    factor_type: str  # "upgrade" 或 "downgrade"
    factor_name: str  # 因素名称
    matched_text: str  # 匹配到的文本片段
    evidence_strength: str  # "强" | "中" | "弱"

@dataclass
class GRADEDetailedDecisionCard:
    """GRADE分级决策卡（全链路溯源）"""
    # 文献基本信息
    paper_title: str
    paper_journal: str
    paper_year: str

    # 初始分级（正则硬规则）
    initial_study_type: str  # 研究类型
    initial_level: str  # 初始等级
    initial_reason: str  # 初始分级依据
    matched_pattern: str  # 匹配到的正则模式

    # 升降级因素（正则硬规则）
    upgrade_factors: List[dict]  # 升级因素列表
    downgrade_factors: List[dict]  # 降级因素列表
    net_adjustment: int  # 净调整值（-3到+3）

    # 最终等级
    final_level: str  # 最终等级
    adjustment_path: str  # 调整路径说明

    # 适用场景和局限性
    applicable_scenarios: List[str]  # 适用场景
    limitations: List[str]  # 局限性

    # 原始等级字符串（保持兼容）
    original_level_str: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    def to_display_format(self) -> str:
        """生成人类可读的显示格式"""
        lines = [
            "=" * 80,
            f"📊 GRADE 分级决策卡",
            "=" * 80,
            "",
            "📄 文献信息",
            f"  标题: {self.paper_title}",
            f"  期刊: {self.paper_journal}",
            f"  年份: {self.paper_year}",
            "",
            "🎯 初始分级（正则硬规则）",
            f"  研究类型: {self.initial_study_type}",
            f"  初始等级: {self.initial_level}",
            f"  分级依据: {self.initial_reason}",
            f"  匹配模式: {self.matched_pattern}",
            "",
        ]

        if self.upgrade_factors:
            lines.append("⬆️ 升级因素")
            for i, factor in enumerate(self.upgrade_factors, 1):
                lines.append(f"  {i}. {factor['name']} ({factor['strength']})")
                lines.append(f"     证据: {factor['matched_text']}")
            lines.append("")

        if self.downgrade_factors:
            lines.append("⬇️ 降级因素")
            for i, factor in enumerate(self.downgrade_factors, 1):
                lines.append(f"  {i}. {factor['name']} ({factor['strength']})")
                lines.append(f"     证据: {factor['matched_text']}")
            lines.append("")

        lines.extend([
            "🎲 最终等级",
            f"  净调整值: {self.net_adjustment:+d}",
            f"  调整路径: {self.adjustment_path}",
            f"  最终等级: {self.final_level}",
            "",
            "✅ 适用场景",
        ])

        for scenario in self.applicable_scenarios:
            lines.append(f"  • {scenario}")

        lines.extend([
            "",
            "⚠️ 局限性",
        ])

        for limitation in self.limitations:
            lines.append(f"  • {limitation}")

        lines.extend([
            "",
            "=" * 80,
        ])

        return "\n".join(lines)

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

# ==================== 降级因素正则硬规则 ====================
DOWNGRADE_RULES = {
    # 1. 研究局限性
    "study_limitations": {
        "name": "研究局限性",
        "patterns": [
            r"(small\s+sample\s+size|样本量.*?小|样本.*?不足|limited.*?sample)",
            r"(lack\s+of\s+blinding|未.*?盲|非.*?盲|no\s+blinding)",
            r"(high\s+dropout\s+rate|高.*?失访|大量.*?退出|high\s+attrition)",
            r"(selection\s+bias|选择.*?偏倚|selection\s+error)",
            r"(incomplete\s+follow.?up|随访.*?不完全|失访.*?多)",
        ],
        "strength": "中"
    },
    # 2. 不精确性
    "imprecision": {
        "name": "不精确性",
        "patterns": [
            r"(wide\s+confidence\s+interval|置信区间.*?宽|ci.*?wide)",
            r"(statistically.*?insignificant|不显著|p.*?>.*?0\.05|no\s+significant\s+difference)",
            r"(low\s+statistical\s+power|统计效能.*?低|power.*?insufficient)",
            r"(small\s+effect\s+size|效应量.*?小|effect.*?minimal)",
        ],
        "strength": "强"
    },
    # 3. 发表偏倚
    "publication_bias": {
        "name": "发表偏倚",
        "patterns": [
            r"(industry.?funded|企业.*?资助|pharma.*?sponsored)",
            r"(conflict\s+of\s+interest|利益.*?冲突|conflict)",
            r"(non.?peer.?reviewed|非.*?同行.*?评议|not.*?peer.*?review)",
            r"(small\s+journal|小.*?期刊|minor.*?journal)",
        ],
        "strength": "中"
    },
    # 4. 不一致性
    "inconsistency": {
        "name": "不一致性",
        "patterns": [
            r"(conflicting\s+results|结果.*?不一致|contradictory\s+findings)",
            r"(heterogeneity.*?high|异质性.*?高|substantial\s+heterogeneity)",
            r"(varying\s+outcomes|结果.*?变化|inconsistent\s+results)",
            r"(different\s+subgroups.*?showed.*?different\s+effects|不同.*?亚组.*?不同)",
        ],
        "strength": "强"
    },
    # 5. 间接性
    "indirectness": {
        "name": "间接性",
        "patterns": [
            r"(surrogate\s+endpoint|替代.*?终点|surrogate\s+outcome)",
            r"(different\s+population|人群.*?不同|not.*?target\s+population)",
            r"(indirect\s+comparison|间接.*?比较|network\s+meta)",
            r"(extrapolation.*?caution|外推.*?谨慎|limited\s+generalizability)",
        ],
        "strength": "中"
    },
}

# ==================== 升级因素正则硬规则 ====================
UPGRADE_RULES = {
    # 1. 效应量大
    "large_effect": {
        "name": "效应量大",
        "patterns": [
            r"(risk\s+ratio.*?[<>].*?[0-9]\.[5-9]|rr.*?[<>].*?[0-9]\.[5-9])",
            r"(odds\s+ratio.*?[<>].*?[0-9]\.[5-9]|or.*?[<>].*?[0-9]\.[5-9])",
            r"(hazard\s+ratio.*?[<>].*?[0-9]\.[5-9]|hr.*?[<>].*?[0-9]\.[5-9])",
            r"(risk\s+reduction.*?>.*?50%|风险.*?降低.*?>.*?50%)",
            r"(highly\s+significant|高度显著|p.*?<.*?0\.001)",
            r"(dramatic\s+improvement|显著.*?改善|substantial\s+benefit)",
        ],
        "strength": "强"
    },
    # 2. 剂量反应关系
    "dose_response": {
        "name": "剂量反应关系",
        "patterns": [
            r"(dose.?response.*?relationship|剂量.*?反应.*?关系|dose.?response\s+curve)",
            r"(dose.?dependent|剂量.*?依赖|dose.?related)",
            r"(dose.?escalation|剂量.*?递增|increasing\s+dose)",
            r"(trend.*?significant|趋势.*?显著|dose.*?trend)",
        ],
        "strength": "强"
    },
    # 3. 混杂因素调整
    "confounding_adjusted": {
        "name": "混杂因素调整",
        "patterns": [
            r"(adjusted\s+for.*?confounders|调整.*?混杂|controlled\s+for)",
            r"(multivariate\s+analysis|多变量.*?分析|multivariate\s+adjustment)",
            r"(propensity\s+score\s+matching|倾向.*?评分.*?匹配|psm)",
            r"(sensitivity\s+analysis.*?robust|敏感性.*?分析.*?稳健)",
            r"(adjusted\s+hazard\s+ratio|调整.*?风险比|adjusted\s+rr)",
        ],
        "strength": "中"
    },
}

# ==================== 适用场景映射 ====================
APPLICABLE_SCENARIOS_MAP = {
    GRADELevel.HIGH: [
        "临床实践指南推荐（A级推荐）",
        "制定诊疗标准和临床路径",
        "卫生政策和医保决策",
        "大规模医疗质量评估",
    ],
    GRADELevel.MODERATE: [
        "临床实践指南推荐（B级推荐）",
        "个体化治疗决策参考",
        "临床研究设计参考",
        "继续医学教育内容",
    ],
    GRADELevel.LOW: [
        "临床实践指南推荐（C级推荐）",
        "探索性研究参考",
        "假设生成和初步结论",
        "患者教育和沟通材料",
    ],
    GRADELevel.VERY_LOW: [
        "临床参考和背景知识",
        "研究假设生成",
        "专家意见参考",
        "教学案例和文献综述",
    ],
}

# ==================== 局限性映射 ====================
LIMITATIONS_MAP = {
    GRADELevel.HIGH: [
        "可能存在未检测到的偏倚",
        "不同人群适用性需验证",
        "长期随访数据可能不足",
    ],
    GRADELevel.MODERATE: [
        "证据质量受限于研究设计或样本量",
        "结果可能随更多研究而改变",
        "需要更多高质量研究验证",
    ],
    GRADELevel.LOW: [
        "证据可靠性有限，谨慎使用",
        "可能受显著偏倚影响",
        "结论需要更高证据支持",
    ],
    GRADELevel.VERY_LOW: [
        "证据质量极低，仅作参考",
        "研究结果可能不可靠",
        "不建议单独作为决策依据",
    ],
}

# ==================== 正则硬规则初始分级（增强版） ====================
def _get_initial_grade_strict(paper: Dict[str, Any]) -> Tuple[GRADELevel, str, str, str]:
    """
    正则硬规则初始分级（完全禁用LLM）
    返回：(初始等级, 分类原因, 研究类型, 匹配到的模式)
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
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            initial_level = GRADE_CONFIG["initial_level"].get(study_type, GRADELevel.VERY_LOW)
            matched_text = match.group(0)
            return initial_level, f"正则匹配到{reason}", study_type.value, matched_text

    # 兜底：极低级
    return GRADELevel.VERY_LOW, "未匹配到具体类型，使用兜底极低级", StudyType.EXPERT_OPINION.value, ""

# ==================== 降级因素正则匹配 ====================
def _match_downgrade_factors(abstract: str) -> List[dict]:
    """
    使用正则硬规则匹配降级因素
    返回：降级因素列表
    """
    factors = []
    abstract_lower = abstract.lower()

    for rule_key, rule_info in DOWNGRADE_RULES.items():
        for pattern in rule_info["patterns"]:
            match = re.search(pattern, abstract_lower, re.IGNORECASE)
            if match:
                matched_text = match.group(0)
                # 提取上下文（前后各30字符）
                start = max(0, match.start() - 30)
                end = min(len(abstract), match.end() + 30)
                context = abstract[start:end].strip()

                factors.append({
                    "rule_key": rule_key,
                    "name": rule_info["name"],
                    "strength": rule_info["strength"],
                    "matched_text": matched_text,
                    "context": context,
                })
                break  # 每个规则只匹配一次

    return factors

# ==================== 升级因素正则匹配 ====================
def _match_upgrade_factors(abstract: str) -> List[dict]:
    """
    使用正则硬规则匹配升级因素
    返回：升级因素列表
    """
    factors = []
    abstract_lower = abstract.lower()

    for rule_key, rule_info in UPGRADE_RULES.items():
        for pattern in rule_info["patterns"]:
            match = re.search(pattern, abstract_lower, re.IGNORECASE)
            if match:
                matched_text = match.group(0)
                # 提取上下文（前后各30字符）
                start = max(0, match.start() - 30)
                end = min(len(abstract), match.end() + 30)
                context = abstract[start:end].strip()

                factors.append({
                    "rule_key": rule_key,
                    "name": rule_info["name"],
                    "strength": rule_info["strength"],
                    "matched_text": matched_text,
                    "context": context,
                })
                break  # 每个规则只匹配一次

    return factors

# ==================== 计算净调整值 ====================
def _calculate_net_adjustment(upgrade_factors: List[dict], downgrade_factors: List[dict]) -> int:
    """
    计算净调整值
    升级因素数 - 降级因素数，限制在[-3, 3]范围内
    """
    # 计算调整值（根据因素强度加权）
    adjustment = 0

    for factor in upgrade_factors:
        if factor["strength"] == "强":
            adjustment += 1
        elif factor["strength"] == "中":
            adjustment += 0.5

    for factor in downgrade_factors:
        if factor["strength"] == "强":
            adjustment -= 1
        elif factor["strength"] == "中":
            adjustment -= 0.5

    # 四舍五入并限制范围
    net_adjustment = int(round(adjustment))
    net_adjustment = max(-3, min(3, net_adjustment))

    return net_adjustment

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

# ==================== 主函数：GRADE证据分级（正则硬规则全链路溯源） ====================
def get_evidence_level(paper: Dict[str, Any]) -> Tuple[GRADELevel, Dict[str, Any]]:
    """
    严格遵循GRADE官方标准进行证据分级（正则硬规则全链路溯源）
    第一步：正则硬规则初始分级（完全禁用LLM）
    第二步：正则硬规则升降级因素匹配（不调用LLM）
    返回：(GRADE等级, 分级详情字典)，详情包含完整决策卡
    """
    # 初始化详情字典（完整可溯源）
    grade_details = {
        "initial_level": "",
        "initial_reason": "",
        "net_adjustment": 0,
        "upgrade_factors": [],
        "downgrade_factors": [],
        "final_level": "",
        "calculation_steps": [],
        "decision_card": None  # 完整决策卡对象
    }

    try:
        # ========== 第一步：正则硬规则初始分级 ==========
        initial_level, initial_reason, study_type, matched_pattern = _get_initial_grade_strict(paper)
        grade_details["initial_level"] = initial_level.value
        grade_details["initial_reason"] = initial_reason
        grade_details["calculation_steps"].append(f"第一步：正则硬规则分级 -> {initial_level.value}")

        # ========== 第二步：正则硬规则升降级因素匹配 ==========
        abstract = paper.get("abstract", "")
        upgrade_factors = _match_upgrade_factors(abstract)
        downgrade_factors = _match_downgrade_factors(abstract)
        net_adjustment = _calculate_net_adjustment(upgrade_factors, downgrade_factors)

        grade_details["upgrade_factors"] = upgrade_factors
        grade_details["downgrade_factors"] = downgrade_factors
        grade_details["net_adjustment"] = net_adjustment

        if net_adjustment > 0:
            grade_details["calculation_steps"].append(f"第二步：识别到{len(upgrade_factors)}个升级因素，{len(downgrade_factors)}个降级因素 -> 净调整值+{net_adjustment}")
        elif net_adjustment < 0:
            grade_details["calculation_steps"].append(f"第二步：识别到{len(upgrade_factors)}个升级因素，{len(downgrade_factors)}个降级因素 -> 净调整值{net_adjustment}")
        else:
            grade_details["calculation_steps"].append("第二步：未识别到净调整因素 -> 净调整值0")

        # ========== 计算最终等级 ==========
        final_level = _calculate_final_level(initial_level, net_adjustment)
        grade_details["final_level"] = final_level.value

        # 记录最终结果
        grade_details["calculation_steps"].append(f"最终等级：{initial_level.value} + {net_adjustment:+d} = {final_level.value}")

        # ========== 生成完整GRADE决策卡 ==========
        # 调整路径说明
        if net_adjustment > 0:
            adjustment_path = f"{initial_level.value} 因{len(upgrade_factors)}个升级因素上调{net_adjustment}级至{final_level.value}"
        elif net_adjustment < 0:
            adjustment_path = f"{initial_level.value} 因{len(downgrade_factors)}个降级因素下调{abs(net_adjustment)}级至{final_level.value}"
        else:
            adjustment_path = f"{initial_level.value} 无显著升降级因素，保持{final_level.value}"

        # 适用场景和局限性
        applicable_scenarios = APPLICABLE_SCENARIOS_MAP.get(final_level, [])
        limitations = LIMITATIONS_MAP.get(final_level, [])

        # 创建决策卡对象
        decision_card = GRADEDetailedDecisionCard(
            paper_title=paper.get("title", ""),
            paper_journal=paper.get("journal", ""),
            paper_year=str(paper.get("year", "")),
            initial_study_type=study_type,
            initial_level=initial_level.value,
            initial_reason=initial_reason,
            matched_pattern=matched_pattern,
            upgrade_factors=upgrade_factors,
            downgrade_factors=downgrade_factors,
            net_adjustment=net_adjustment,
            final_level=final_level.value,
            adjustment_path=adjustment_path,
            applicable_scenarios=applicable_scenarios,
            limitations=limitations,
            original_level_str=final_level.value  # 保留原等级字符串
        )

        grade_details["decision_card"] = decision_card.to_dict()

        logger.info(f"GRADE分级完成：{paper.get('title', '')[:50]}... -> {initial_level.value} -> {final_level.value} (调整{net_adjustment:+d})")

    except Exception as e:
        # 异常时兜底
        logger.error(f"GRADE分级计算失败: {e}", exc_info=True)
        final_level = GRADELevel.VERY_LOW
        grade_details["final_level"] = final_level.value
        grade_details["initial_level"] = GRADELevel.VERY_LOW.value
        grade_details["initial_reason"] = f"系统异常：{str(e)}"
        grade_details["calculation_steps"].append("系统异常，使用兜底等级")

        # 异常时生成简化的决策卡
        decision_card = GRADEDetailedDecisionCard(
            paper_title=paper.get("title", ""),
            paper_journal=paper.get("journal", ""),
            paper_year=str(paper.get("year", "")),
            initial_study_type=StudyType.EXPERT_OPINION.value,
            initial_level=GRADELevel.VERY_LOW.value,
            initial_reason=f"系统异常：{str(e)}",
            matched_pattern="",
            upgrade_factors=[],
            downgrade_factors=[],
            net_adjustment=0,
            final_level=GRADELevel.VERY_LOW.value,
            adjustment_path="系统异常，使用兜底等级",
            applicable_scenarios=LIMITATIONS_MAP.get(GRADELevel.VERY_LOW, []),
            limitations=["系统异常，无法准确评估"],
            original_level_str=GRADELevel.VERY_LOW.value
        )
        grade_details["decision_card"] = decision_card.to_dict()

    return final_level, grade_details

# ==================== 批量分级函数（推荐使用） ====================
def get_evidence_levels_batch(papers: List[Dict[str, Any]]) -> List[Tuple[GRADELevel, Dict[str, Any]]]:
    """
    批量GRADE证据分级（推荐使用）
    使用正则硬规则全链路溯源，不调用LLM
    返回：[(等级1, 详情1), (等级2, 详情2), ...]，每个详情包含完整决策卡
    """
    results = []

    # 批量处理所有文献
    for paper in papers:
        level, details = get_evidence_level(paper)
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

# ==================== 决策卡显示辅助函数 ====================
def get_decision_card_display(grade_details: Dict[str, Any]) -> str:
    """
    从分级详情中生成人类可读的决策卡显示格式
    用于在UI中展示完整的GRADE分级决策过程
    """
    decision_card_dict = grade_details.get("decision_card")
    if not decision_card_dict:
        return "决策卡数据不可用"

    # 重建决策卡对象以使用其显示方法
    try:
        decision_card = GRADEDetailedDecisionCard(
            paper_title=decision_card_dict.get("paper_title", ""),
            paper_journal=decision_card_dict.get("paper_journal", ""),
            paper_year=decision_card_dict.get("paper_year", ""),
            initial_study_type=decision_card_dict.get("initial_study_type", ""),
            initial_level=decision_card_dict.get("initial_level", ""),
            initial_reason=decision_card_dict.get("initial_reason", ""),
            matched_pattern=decision_card_dict.get("matched_pattern", ""),
            upgrade_factors=decision_card_dict.get("upgrade_factors", []),
            downgrade_factors=decision_card_dict.get("downgrade_factors", []),
            net_adjustment=decision_card_dict.get("net_adjustment", 0),
            final_level=decision_card_dict.get("final_level", ""),
            adjustment_path=decision_card_dict.get("adjustment_path", ""),
            applicable_scenarios=decision_card_dict.get("applicable_scenarios", []),
            limitations=decision_card_dict.get("limitations", []),
            original_level_str=decision_card_dict.get("original_level_str", "")
        )
        return decision_card.to_display_format()
    except Exception as e:
        logger.error(f"生成决策卡显示格式失败: {e}")
        return f"决策卡显示格式生成失败: {str(e)}"

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