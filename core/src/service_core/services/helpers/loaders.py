################################################################################
#                                                                              #
#                      ####### BADEN-WÜRTTEMBERG #######                       #
#                                                                              #
#          A tribute to the land of innovation, culture, and beauty.           #
#          Home of SAP, Brezeln, Ritter Sport, and Kartoffelsalat.             #
#                                                                              #
#                         o__      o__      o__                                #
#                        / < \_   / < \_   / < \_                              #
#                       (*)/ (*) (*)/ (*) (*)/ (*)                             #
#                                                                              #
#                  "Wir können alles. Außer Hochdeutsch."                      #
#                                                                              #
################################################################################
from typing import Final


def load_prompt(prompt_path: str) -> str:
    """
    Loads prompt templates from a JSON file.

    Args:
        prompt_path (str): Path to the JSON file containing prompt templates.

    Returns:
        str: The contents of the prompt file as a string.
    """
    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()
