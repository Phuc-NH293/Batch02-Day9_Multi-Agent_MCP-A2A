"""Bài Tập 2: Thêm Tools và Knowledge Base

Hoàn thành các TODO để thêm tool và knowledge base entry mới.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from common.llm import get_llm

# Knowledge base
LEGAL_KNOWLEDGE = [
    {
        "id": "ucc_breach",
        "keywords": ["breach", "contract", "remedies", "damages", "ucc"],
        "text": (
            "Under the Uniform Commercial Code (UCC) Article 2, remedies for breach of contract "
            "include: (1) expectation damages; (2) consequential damages; (3) specific performance; "
            "(4) cover damages. Statute of limitations is typically 4 years (UCC § 2-725)."
        ),
    },
    {
        "id": "labor_law",
        "keywords": [
            "lao động",
            "lao dong",
            "sa thải",
            "sa thai",
            "hợp đồng lao động",
            "hop dong lao dong",
            "tiền lương",
            "tien luong",
            "tranh chấp lao động",
            "tranh chap lao dong",
            "người lao động",
            "nguoi lao dong",
        ],
        "text": (
            "Theo Bộ luật Lao động Việt Nam, tranh chấp lao động thường liên quan đến "
            "hợp đồng lao động, tiền lương, kỷ luật lao động, sa thải, đơn phương chấm dứt "
            "hợp đồng và bồi thường. Người lao động có thể yêu cầu hòa giải, trọng tài lao "
            "động hoặc khởi kiện ra tòa tùy loại tranh chấp."
        ),
    },
]


@tool
def search_legal_knowledge(query: str) -> str:
    """Tìm kiếm trong knowledge base pháp lý."""
    query_lower = query.lower()
    for entry in LEGAL_KNOWLEDGE:
        if any(kw in query_lower for kw in entry["keywords"]):
            return f"[{entry['id']}] {entry['text']}"
    return "Không tìm thấy thông tin liên quan."


@tool
def check_statute_of_limitations(case_type: str) -> str:
    """Kiểm tra thời hiệu khởi kiện theo loại vụ việc."""
    case_type_lower = case_type.lower()

    if any(kw in case_type_lower for kw in ["ucc", "contract", "hợp đồng", "hop dong"]):
        return (
            "Thời hiệu tham khảo cho tranh chấp hợp đồng: 3 năm theo pháp luật dân sự/"
            "thương mại Việt Nam; riêng hợp đồng mua bán hàng hóa theo UCC thường là 4 năm "
            "(UCC § 2-725)."
        )

    if any(kw in case_type_lower for kw in ["lao động", "lao dong", "sa thải", "sa thai"]):
        return (
            "Thời hiệu tham khảo cho tranh chấp lao động cá nhân: thường là 1 năm kể từ ngày "
            "phát hiện quyền/lợi ích hợp pháp bị xâm phạm. Một số loại yêu cầu có thể có "
            "mốc thời gian riêng."
        )

    if any(kw in case_type_lower for kw in ["tort", "dân sự", "dan su", "bồi thường", "boi thuong"]):
        return "Thời hiệu tham khảo cho yêu cầu bồi thường/tranh chấp dân sự: thường là 3 năm."

    return (
        "Chưa xác định được loại vụ việc. Hãy nêu rõ ví dụ: 'hợp đồng', 'lao động', "
        "'sa thải' hoặc 'bồi thường dân sự'."
    )


async def main():
    load_dotenv()
    llm = get_llm()
    
    tools = [search_legal_knowledge, check_statute_of_limitations]
    tool_map = {tool_item.name: tool_item for tool_item in tools}
    llm_with_tools = llm.bind_tools(tools)
    
    question = "Thời hiệu khởi kiện vụ vi phạm hợp đồng là bao lâu?"
    
    messages = [
        SystemMessage(content="Bạn là chuyên gia pháp lý. Sử dụng tools để tra cứu thông tin."),
        HumanMessage(content=question),
    ]
    
    print(f"Câu hỏi: {question}\n")
    
    # First LLM call - decide which tools to use
    response = await llm_with_tools.ainvoke(messages)
    messages.append(response)
    
    # Execute tools if requested
    if response.tool_calls:
        for tool_call in response.tool_calls:
            print(f"🔧 Gọi tool: {tool_call['name']}")
            tool_result = None
            tool_fn = tool_map.get(tool_call["name"])
            if tool_fn:
                tool_result = tool_fn.invoke(tool_call["args"])
            
            if tool_result:
                messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call["id"]))
        
        # Second LLM call - synthesize final answer
        final_response = await llm_with_tools.ainvoke(messages)
        print(f"\n✅ Kết quả:\n{final_response.content}")
    else:
        print(f"\n✅ Kết quả:\n{response.content}")


if __name__ == "__main__":
    asyncio.run(main())
