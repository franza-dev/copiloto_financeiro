from google import genai
from google.genai import types
import json
import os
from dotenv import load_dotenv

load_dotenv()

CHAVE_API = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=CHAVE_API)

PROMPT_SISTEMA = """
Você é um assistente financeiro de alta precisão. Sua tarefa é converter frases ou áudios em dados JSON.

IDENTIFIQUE A INTENÇÃO DO USUÁRIO:
1. DEFINIR LIMITE/TETO: Se o usuário quer estabelecer um valor máximo para uma categoria (ex: "meu teto de Uber é 500", "limite de 200 para lazer").
   - "natureza": "config_limite"
   - "categoria": Nome da categoria (ex: "Uber", "Lazer")
   - "valor": O valor do limite (float positivo)
   - Preencha os demais campos como "" ou "PF".

2. LANÇAMENTO DE TRANSAÇÃO: Se o usuário relata um gasto ou ganho real.
   - "natureza": "saida" (pagamentos, gastos, transferir para fora) ou "entrada" (recebimentos, pix recebido).
   - "valor": O número (float sempre positivo).
   - "descricao": O que foi feito.
   - "categoria": Classificação (ex: Alimentação, Transporte).
   - "tipo": "PF" ou "PJ" (padrão "PF" se não houver indicação).
   - "banco": Nome do banco citado (ex: Nubank, Asaas).

REGRAS DE OURO:
- Responda APENAS o JSON puro.
- NUNCA use aspas triplas (```json).
- Se não entender algo, coloque "A Classificar" na categoria.
"""

def processar_texto_ia(texto):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{PROMPT_SISTEMA}\n\nFrase do usuário: '{texto}'"
        )
        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"Erro Texto IA: {e}")
        return {"descricao": "Erro", "valor": 0, "natureza": "saida", "categoria": "Erro"}

def processar_audio_ia(caminho_audio):
    try:
        # 1. Upload do arquivo para o servidor do Google
        with open(caminho_audio, "rb") as f:
            arquivo_gemini = client.files.upload(
                file=f,
                config=types.UploadFileConfig(display_name=caminho_audio)
            )

        # 2. Processamento multimodal
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[PROMPT_SISTEMA, arquivo_gemini]
        )

        # 3. Limpeza do arquivo no Google
        client.files.delete(name=arquivo_gemini.name)

        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        print(f"Erro Áudio IA: {e}")
        return {"descricao": "Erro de Áudio", "valor": 0, "natureza": "saida", "categoria": "Erro"}
