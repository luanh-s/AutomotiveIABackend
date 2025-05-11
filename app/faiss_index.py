import faiss
import openai
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def gerar_embedding(texto):
    response = openai.Embedding.create(
        model="text-embedding-3-small",
        input=texto
    )
    return np.array(response["data"][0]["embedding"], dtype=np.float32)

class FaissRAG:
    def __init__(self, dim=1536):
        self.index = faiss.IndexFlatL2(dim)
        self.textos = []

    def adicionar_texto(self, texto):
        vetor = gerar_embedding(texto)
        self.index.add(np.array([vetor]))
        self.textos.append(texto)

    def consultar(self, pergunta, k=3):
        vetor = gerar_embedding(pergunta)
        dist, indices = self.index.search(np.array([vetor]), k)
        return [self.textos[i] for i in indices[0]]
