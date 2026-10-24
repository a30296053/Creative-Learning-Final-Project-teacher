"""主要流程。這是空殼：每個 TODO 都要換成你們自己的實作。

目前的流程：
  護欄檢查 → 檢索 → 產生回覆（Ollama 地端模型）
可以自由改成 Agent、加上路由、加上 Fact Critic 等。
唯一的要求是最後回傳的 ChatResponse 符合 spec/api-contract.md。
"""

from collections import defaultdict

import httpx

from .config import LLM_TEMPERATURE, LOCAL_MODEL, OLLAMA_URL
from .rag.retrieve import retrieve as rag_retrieve
from .rag.retrieve import section_chunks
from .schemas import ChatResponse, Guardrail, Source, TraceStep

SYSTEM_PROMPT = """你是國中數學教師的 AI 助教，教材是「一元一次方程式」講義。請用繁體中文回答。
規則：
1. 只能依據下方【參考資料】回答，不可使用資料以外的知識，也不可自行補充或推測。
2. 資料中沒有的內容，直接說「教材中沒有提到」。
3. 回答中引用內容時，在句尾標註段落 id，例如 [1-3-3]。
4. 算式用純文字書寫（例如 3x + 5 = 20），不要使用 LaTeX。
5. 摘要或整理時，涵蓋參考資料中每一段的重點，並維持教材的原意。

【參考資料】
{context}"""

# session_id → 對話歷史。重啟就會消失，有需要請自行換成持久化儲存
_history: dict[str, list[dict]] = defaultdict(list)


def check_guardrail(message: str, trace: list[TraceStep]) -> Guardrail:
    # TODO: 依角色實作護欄（家教：索答偵測；家長：高風險分類……）
    trace.append(TraceStep(step="guardrail", detail="尚未實作，一律放行"))
    return Guardrail()


def retrieve(message: str, trace: list[TraceStep]) -> list[Source]:
    whole = section_chunks(message)
    if whole:
        hits = [(c, 1.0) for c in whole]
        detail = "依節號取得整節：" + ", ".join(c.id for c in whole)
    else:
        hits = rag_retrieve(message)
        detail = ", ".join(f"{c.id}({score:.3f})" for c, score in hits)
    trace.append(TraceStep(step="retrieve", detail=detail))
    # 一塊涵蓋多段時，每段各列一筆（目前一塊只有一段）
    return [Source(id=i, text=c.text) for c, _ in hits for i in c.ids]


def generate_local(messages: list[dict]) -> str:
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": LOCAL_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": LLM_TEMPERATURE},
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def handle(session_id: str, message: str) -> ChatResponse:
    trace: list[TraceStep] = []
    history = _history[session_id]

    guardrail = check_guardrail(message, trace)
    # TODO: 護欄觸發時改走對應的處理（鷹架引導、轉介、拒絕……）

    sources = retrieve(message, trace)
    context = "\n\n".join(f"[{s.id}] {s.text}" for s in sources)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context or "（無）")},
        *history,
        {"role": "user", "content": message},
    ]
    # TODO: 依需求路由到地端或雲端模型，並如實回報 route
    answer = generate_local(messages)
    trace.append(TraceStep(step="generate", detail=f"使用地端模型 {LOCAL_MODEL}"))

    history += [{"role": "user", "content": message}, {"role": "assistant", "content": answer}]

    return ChatResponse(
        answer=answer,
        route="local",
        guardrail=guardrail,
        sources=sources,
        trace=trace,
    )
