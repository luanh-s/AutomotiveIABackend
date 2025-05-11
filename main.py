
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.faiss_index import FaissRAG
from app.salesforce_client import buscar_contato_e_veiculos
import requests, logging, os
import openai

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Configuração correta de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pode ser restringido para ["http://localhost"] em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa FaissRAG
rag = FaissRAG()
with open("data/articles.txt", "r", encoding="utf-8") as f:
    for artigo in f.read().split("\n---\n"):
        rag.adicionar_texto(artigo.strip())

# Configuração da chave da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")  # Ou defina diretamente: openai.api_key = "sua-chave-aqui"

def consultar_llama(prompt):
    try:
        res = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        })
        res.raise_for_status()
        return res.json()["response"]
    except Exception as e:
        logging.error(f"Erro ao consultar LLaMA: {str(e)}")
        return "Erro ao gerar resposta com LLaMA local."

def consultar_chatgpt(prompt):
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return resposta['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"Erro ao consultar ChatGPT: {str(e)}")
        return "Erro ao gerar resposta com ChatGPT."

@app.post("/ask")
async def ask_agent(request: Request):
    data = await request.json()
    pergunta = data.get("message", "")
    modelo = data.get("modelo", "chatgpt")  # "chatgpt" é o padrão
    user_id = data.get("user_id", None)

    contextos = rag.consultar(pergunta)

    contexto_usuario = ""
    if user_id:
        try:
            user = buscar_contato_e_veiculos(user_id)
            logging.info(f"user: {repr(user)}")
            if user:
                contexto_usuario += f"Usuário: {user.get('nome', 'Desconhecido')}\n"

                veiculos = user.get("veiculos", [])
                if veiculos:
                    contexto_usuario += "Veículos:\n"
                    for v in veiculos:
                        contexto_usuario += (
                            f"- {v.get('make', 'Marca desconhecida')} "
                            f"{v.get('model', 'Modelo desconhecido')} "
                            f"{v.get('year', 'Ano desconhecido')} "
                            f"(VIN: {v.get('vin', 'N/A')})\n"
                        )
                else:
                    contexto_usuario += "Nenhum veículo encontrado.\n"

                contexto_usuario += "\n"

        except Exception as e:
            logging.warning(f"Erro ao obter dados do usuário: {e}")
            contexto_usuario += "Erro ao obter dados do usuário.\n\n"

    prompt = f"{contexto_usuario}O cliente perguntou: \"{pergunta}\"\n\n"
    prompt += "Baseado nos seguintes artigos técnicos:\n"
    prompt += "\n".join(f"- {c}" for c in contextos)
    prompt += "\n\nResponda de forma clara e objetiva."

    logging.info(f"prompt: {prompt}")
    
    if modelo == "chatgpt":
        resposta = consultar_chatgpt(prompt)
    else:
        resposta = consultar_llama(prompt)

    return {"resposta": resposta}
