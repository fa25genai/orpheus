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
from typing import cast, Any

from langchain_core.language_models import BaseLanguageModel

from service_core.services.llm_chain.shared_llm import create_base_model


def ask_llm(prompt: str) -> str:
    llm = create_llm()
    response = llm.invoke(prompt)
    if isinstance(response, str):
        return response
    return getattr(response, "content", response)


def create_llm() -> BaseLanguageModel[Any]:
    model_name = os.getenv("MODEL_NAME")
    if model_name is None:
        raise ValueError("MODEL_NAME environment variable is not set")

    llm = create_base_model(model_name)
    return llm
