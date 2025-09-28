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
