import chainlit as cl
import openai
import os
import base64
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT
from langsmith import traceable
from langsmith.wrappers import wrap_openai

import requests
from bs4 import BeautifulSoup

load_dotenv()

configurations = {
    "openai_gpt-4":{
        "endpoint_url": os.getenv("OPENAI_ENDPOINT"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-4o-mini"
    }
}

# Choose configuration
config_key = "openai_gpt-4"

# get the configuration
config = configurations[config_key]

client = wrap_openai(openai.AsyncClient(api_key=config["api_key"], base_url=config["endpoint_url"]))

gen_kwargs = {
    "model": config["model"],
    "temperature": 0.3,
    "max_tokens": 500
}

# Configuration setting to enable or disable the system prompt
ENABLE_SYSTEM_PROMPT = True

@traceable
@cl.on_message
async def on_message(message: cl.Message):
    # Maintain an array of messages in the user session
    message_history = cl.user_session.get("message_history", [])

    if ENABLE_SYSTEM_PROMPT and (not message_history or message_history[0].get("role") != "system"):
        system_prompt_content = SYSTEM_PROMPT
        message_history.insert(0, {"role":"system", "content": system_prompt_content})

    message_history.append({"role": "user", "content": message.content})
    
    # TODO: We will assess the assess the message here for quality and relevance
    # asyncio.create_task(assess_message(message_history))

    response_message = cl.Message(content="")
    await response_message.send()
    
    # Pass in the full message history for each request
    stream = await client.chat.completions.create(messages=message_history, 
                                                  stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)

    # Record the AI's response in the history
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)
    await response_message.update()

if __name__ == "__main__":
    cl.main()

    