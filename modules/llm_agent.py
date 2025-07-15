from fastapi import APIRouter

router = APIRouter()

@router.post("/ask")
async def ask_agent(payload: dict):
    user_text = payload.get("text", "")
    # TODO: Integrate LangChain with Groq LLM
    # response = langchain_agent_respond(user_text)
    # return {"response": response}
    return {"response": "[Agent response placeholder]"} 