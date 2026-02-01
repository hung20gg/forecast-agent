from typing import Any, Dict, List
from llm import LLM

def count_messages_tokens(messages: List[Dict[str, Any]]) -> int:
    try:
        import tiktoken
    except ImportError:
        raise ImportError("tiktoken library is required for token counting. Please install it via 'pip install tiktoken'.")
    
    total_tokens = 0
    enc = tiktoken.get_encoding("o200k_base")
    for message in messages:
        content = message.get("content", "")

        tokens = enc.encode(content)
        total_tokens += len(tokens)        

    return total_tokens


def count_messages_words(messages: List[Dict[str, Any]]) -> int:
    total_words = 0
    for message in messages:
        content = message.get("content", "")
        words = content.split()
        total_words += len(words)
    return total_words


def flatten_messages(messages: List[Dict[str, Any]]) -> str:
    return "\n".join([f"## {msg['role'].capitalize()}: \n\n{msg['content']}\n\n" for msg in messages]).strip()


def summarize_messages(llm: LLM, messages: List[Dict[str, Any]]) -> str:
    
    prompt = """
    You are an expert summarization AI. 
    
    Given the following conversation messages, provide a concise summary highlighting the key points discussed.
    
    Maintain language and important details while ensuring clarity and brevity.
    
    {messages}

    ## Note:
    - Only return the summary text without any additional commentary.
    """

    flattened = flatten_messages(messages)
    full_prompt = prompt.replace("{messages}", flattened)
    response = llm.chat_completion([{"role": "user", "content": full_prompt}])
    return response.get("content", "").strip()