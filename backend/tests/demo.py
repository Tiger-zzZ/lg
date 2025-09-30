from typing import Annotated, AsyncIterator, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.ai import AIMessage

import asyncio
import os
from langchain.chat_models import init_chat_model

os.environ["OPENAI_API_KEY"] = "sk-..."
llm = init_chat_model("openai:deepseek-v3-qf", base_url="http://218.17.227.196:18000/v1")
# res = llm.invoke("hi")
# print(res)

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)

    # messages 的类型是 "list"。注解中的 `add_messages` 函数定义了该 state 键的更新方式
    # （这里是将新消息追加到列表中，而不是覆盖原有内容）
    messages: Annotated[list, add_messages]


def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

async def chatbot_async(state: State):
    return {"messages": [await llm.ainvoke(state["messages"])]}

class StreamingState(State):
    messages: list
    streaming: bool = False


graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot_async)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()

# 这里没有实现流式输出的原因是：虽然 graph.stream 方法本身是用于流式处理的，
# 但在当前的 chatbot 实现中，llm.invoke(state["messages"]) 是同步调用，
# 它会等待大模型一次性返回完整结果后才继续执行。
# 因此，event.values() 里的内容也是一次性返回的全部消息，而不是逐步流式输出的 token 或消息片段。
# 如果想要实现真正的流式输出，需要使用支持流式响应的模型接口（如 openai 的 stream=True），
# 并在 chatbot 或 llm.invoke 处处理流式数据，然后在这里逐步打印每个 token 或消息片段。

def stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}], "streaming": True}, stream_mode="values"):
        for value in event.values():
            if isinstance(value[-1], AIMessage):
                print("Assistant:", value[-1].content)
            # print("Assistant:", value)

async def graph_async(user_input: str):
    async for event in graph.astream({"messages": [{"role": "user", "content": user_input}], "streaming": True}, stream_mode="values"):
        for value in event.values():
            if isinstance(value[-1], AIMessage):
                print("Assistant:", value[-1].content)

def main():
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            stream_graph_updates(user_input)
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
            break

if __name__ == "__main__":
    # main()
    asyncio.run(graph_async("讲个笑话"))