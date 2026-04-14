import warnings
import os
warnings.filterwarnings("ignore")
import httpx
import unicodedata
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    http_client=httpx.Client(verify=False)
)

# --- FUNÇÃO DE NORMALIZAÇÃO ---
def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower()
    if texto.endswith("s"):
        texto = texto[:-1]
    return texto

# perfil do usuário (memória real)
perfil = {
    "nome": None,
    "gostos": []
}

# histórico
mensagens = [
    {
        "role": "system",
        "content": (
            "Você é um assistente direto, objetivo e amigável. "
            "Responda curto e sem enrolação."
        )
    }
]

# modelo da requisição
class Pergunta(BaseModel):
    texto: str

@app.get("/")
def raiz():
    return {"mensagem": "API do Chatbot funcionando!"}

@app.post("/chat")
def chat(pergunta: Pergunta):
    global perfil, mensagens
    texto_usuario = pergunta.texto.strip().lower()

    if not texto_usuario:
        return {"resposta": ""}

    # --- LIMPAR MEMÓRIA ---
    if texto_usuario == "limpar memoria":
        perfil["nome"] = None
        perfil["gostos"] = []
        return {"resposta": "Pronto! Esqueci tudo sobre você. Pode começar do zero! 🧹"}

    # --- SAUDAÇÃO RELIGIOSA ---
    if "deus abençoe" in texto_usuario:
        return {"resposta": "Amém, você também! 🙏"}

    # --- DETECTA NOME ---
    gatilho_nome = None
    if "meu nome é" in texto_usuario:
        gatilho_nome = "meu nome é"
    elif "eu me chamo" in texto_usuario:
        gatilho_nome = "eu me chamo"
    elif "pode me chamar de" in texto_usuario:
        gatilho_nome = "pode me chamar de"

    if gatilho_nome:
        novo_nome = texto_usuario.split(gatilho_nome)[-1].strip().title()
        if perfil["nome"] == novo_nome:
            return {"resposta": f"Já sei que você se chama {novo_nome}! 😄"}
        else:
            perfil["nome"] = novo_nome
            return {"resposta": f"Atualizado! Agora vou te chamar de {novo_nome}."}

    # --- DETECTA GOSTOS ---
    if "gosto de" in texto_usuario:
        gosto = texto_usuario.split("gosto de")[-1].strip()
        if any(normalizar(g) == normalizar(gosto) for g in perfil["gostos"]):
            return {"resposta": f"Já sei que você gosta de {gosto}! 😄"}
        else:
            perfil["gostos"].append(gosto)
            return {"resposta": f"Legal, vou lembrar que você gosta de {gosto}!"}

    # --- CONSULTA PERFIL ---
    if "quem eu sou" in texto_usuario:
        if perfil["nome"] and perfil["gostos"]:
            resposta = f"Você é {perfil['nome']} e gosta de {', '.join(perfil['gostos'])}."
        elif perfil["nome"]:
            resposta = f"Você é {perfil['nome']}, mas ainda não me contou o que gosta."
        elif perfil["gostos"]:
            resposta = f"Ainda não sei seu nome, mas sei que você gosta de {', '.join(perfil['gostos'])}."
        else:
            resposta = "Ainda não sei nada sobre você. Me conta seu nome e o que você gosta! 😊"
        return {"resposta": resposta}

    # --- INJEÇÃO NO CONTEXTO ---
    contexto_extra = ""
    if perfil["nome"]:
        contexto_extra += f"O nome do usuário é {perfil['nome']}. "
    if perfil["gostos"]:
        contexto_extra += f"O usuário gosta de: {', '.join(perfil['gostos'])}. "

    mensagens[0]["content"] = (
        "Você é um assistente direto e objetivo. "
        + contexto_extra +
        "Responda de forma curta."
    )

    mensagens.append({"role": "user", "content": texto_usuario})

    resposta = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=mensagens,
        max_tokens=80,
        temperature=0.3,
        frequency_penalty=0.4,
        presence_penalty=0.2
    )

    texto_resposta = resposta.choices[0].message.content
    mensagens.append({"role": "assistant", "content": texto_resposta})

    if len(mensagens) > 10:
        mensagens = [mensagens[0]] + mensagens[-9:]

    return {"resposta": texto_resposta}
