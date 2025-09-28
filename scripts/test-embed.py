from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import ModelScopeEmbeddings

embeddings = ModelScopeEmbeddings(
    model_id="Qwen/Qwen3-Embedding-8B-GGUF",  # 第三方映射的模型名
)

# 示例调用
vector = embeddings.embed_query("人工智能的发展趋势")
print(len(vector))  # 向量维度

