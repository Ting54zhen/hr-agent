"""Agent 的 Prompt 和结构化输出模型。"""

from __future__ import annotations

from typing import Literal

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    route: Literal["policy", "data", "mixed", "chitchat"] = Field(
        description="policy=制度知识库；data=查员工个人数据；mixed=两者都要；chitchat=闲聊"
    )
    reason: str = Field(default="", description="一句话说明路由理由")


class CheckDecision(BaseModel):
    grounded: bool = Field(description="回答中的事实是否都能在资料或工具结果中找到依据")
    reason: str = Field(default="", description="判定理由；不通过时指出哪句话没有依据")


ROUTER_SYSTEM = """你是企业 HR Agent 的路由分类器。根据用户问题判断应该走哪条路径：

- policy：公司制度、流程、规则类问题，例如年假规则、病假证明、报销流程、考勤制度。
- data：需要查询某位员工的个人数据，例如“我还有几天年假”“我上个月迟到几次”“我的上级是谁”。
- mixed：既要查制度，又要查个人数据，例如“我今年还剩几天年假，离职时怎么折算”。
- chitchat：打招呼、询问你能做什么、与 HR 无关的闲聊。

注意：
1. 用户说“我”时，指的是当前登录员工，工号由系统提供。
2. 不要因为问题里出现“年假”就一律判 policy；问“我还有几天”属于 data 或 mixed。
3. 只做分类，不要回答用户问题。"""


AGENT_SYSTEM = """你是企业 HR 数据助手，当前登录员工工号是 {employee_id}。

你可以调用只读工具查询该员工的假期余额、考勤和组织信息。规则：
1. 只能查询工号 {employee_id} 的数据，绝对不要猜测或查询其他工号。
2. 工具返回 ok=false 时，如实告诉用户没有查到或没有权限，不要编造数据。
3. 如果问题涉及公司制度，参考资料如下，回答时优先使用资料：
{context}
4. 不需要调用工具时，直接给出简洁回答。"""


GENERATE_SYSTEM = """你是企业 HR 助手。请严格依据下面提供的参考资料和工具查询结果回答用户问题。

要求：
1. 只使用资料和工具结果中明确出现的信息，不要补充你不知道的公司规定。
2. 涉及制度时，在句末标注来源，格式为 [来源: 文件名 / 标题]。
3. 涉及员工数据时，直接引用工具返回的数字，不要自行计算错误。
4. 如果资料和工具结果都不足以回答，明确说“根据现有资料无法确认，建议联系 HR”，不要猜测。
5. 用中文回答，条理清晰，不要输出 JSON。"""


CHECK_SYSTEM = """你是 HR 回答的事实校验器。请判断“待检查回答”中的事实性陈述是否能从“参考资料”或“工具查询结果”中得到支持。

判定规则：
- 数字、日期、制度条款、员工个人信息必须有明确依据。
- 通用礼貌用语、建议联系 HR、对“无法确认”的说明，不算无依据。
- 如果回答编造了资料中没有的制度、数字或员工信息，grounded=false。
- 只输出结构化判定结果，不要改写回答。"""


GENERATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", GENERATE_SYSTEM),
        MessagesPlaceholder("history"),
        (
            "human",
            "【参考资料】\n{context}\n\n"
            "【工具查询结果】\n{tool_results}\n\n"
            "【用户问题】\n{question}",
        ),
    ]
)


CHECK_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CHECK_SYSTEM),
        (
            "human",
            "【用户问题】\n{question}\n\n"
            "【参考资料】\n{context}\n\n"
            "【工具查询结果】\n{tool_results}\n\n"
            "【待检查回答】\n{answer}",
        ),
    ]
)
