################################################################################
#                                                                              #
#                      ####### BADEN-WÜRTTEMBERG #######                       #
#                                                                              #
#          A tribute to the land of innovation, culture, and nature.           #
#          Home of Lake Constance, Bosch, Heidelberg, and Maultaschen.         #
#                                                                              #
#                         o__      o__      o__                                #
#                        / < \_   / < \_   / < \_                              #
#                       (*)/ (*) (*)/ (*) (*)/ (*)                             #
#                                                                              #
#                  "Wir können alles. Außer Hochdeutsch."                      #
#                                                                              #
################################################################################
import os

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama


def getLLM() -> ChatOllama:
    load_dotenv()

    api_key = os.environ.get("LLAMA_API_KEY", "")
    llm: ChatOllama = ChatOllama(
        model=os.environ.get("LLAMA_MODEL", "gemma3:27b"),
        base_url=os.environ.get("LLAMA_API_URL", "https://gpu.aet.cit.tum.de/ollama"),
        headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
    )
    return llm

def ask_llm(prompt: str):
    llm = getLLM()
    response = llm.invoke(prompt)
    return response.content