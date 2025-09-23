from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_core.language_models.base import BaseLanguageModel
from service_slides.llm_chain.shared_llm import invoke_llm

def test(model: BaseLanguageModel) -> str:
    system = SystemMessagePromptTemplate.from_template(
        "You always answer with 'Hello, AI world!'"
    )

    user = ChatPromptTemplate.from_template(
        "echo '{user_input}'"
    )

    prompt = ChatPromptTemplate.from_messages([system, user])

    print("Invoking LLM...")

    response = invoke_llm(
        model=model,
        prompt=prompt,
        input_data={"user_input": "Hello, AI world!"}
    )
    
    print("LLM Response:", response)

    return response