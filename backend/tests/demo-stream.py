from dataclasses import dataclass

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START

import os

@dataclass
class MyState:
    topic: str
    joke: str = ""

os.environ["OPENAI_API_KEY"] = "sk-..."

llm = init_chat_model("openai:deepseek-v3-qf", base_url="http://218.17.227.196:18000/v1")

import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from typing import Dict, List, Annotated, AsyncIterator
from typing_extensions import TypedDict

class State(TypedDict):
    messages: Annotated[List[Dict], add_messages]

async def call_model(state: State) -> AsyncIterator[State]:
    async for chunk in llm.astream(state["messages"]):
        if chunk.content:
            yield {"messages": [{"role": "assistant", "content": chunk.content}]}

graph = StateGraph(State)
graph.add_node("model", call_model)
graph.add_edge(START, "model")
graph.add_edge("model", END)
app = graph.compile()

async def main():
    inputs = {"messages": [{"role": "user", "content": "请用三句话介绍一下LangGraph"}]}

    print("逐 token 输出:\n")
    async for event in app.astream_events(inputs, stream_mode="messages"):
        if event["event"] == "on_chain_stream" and event["name"] == "LangGraph":
            chunk_data = event["data"]["chunk"]
            
            # 提取内容
            if isinstance(chunk_data[0], AIMessage):
                message_chunk = chunk_data[0]
                if hasattr(message_chunk, 'content') and message_chunk.content:
                    print(message_chunk.content, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
