from langchain_ollama import OllamaLLM
import os

base_url = os.getenv("OLLAMA_HOST")

def get_llm_response(query: str):
    model = OllamaLLM(model="mistral", base_url=base_url)

    prompt = f"Answer the following question: {query}"
    response = model.invoke(prompt)

    return response

def process_input(user_query: str):
    llm_response = get_llm_response(user_query)
    # print("\nLLM Response:\n", llm_response)
    return llm_response
