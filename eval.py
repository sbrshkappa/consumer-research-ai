from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from langsmith.schemas import Run, Example
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from openai import OpenAI
import json
from dotenv import load_dotenv

client = wrap_openai(OpenAI())


load_dotenv()

@traceable
def product_ranking_evaluator(run: Run, example: Example) -> dict:
    inputs = example.inputs['input']
    outputs = example.outputs['output']

    system_prompt = next((msg['data']['content'] for msg in inputs if msg['type'] == 'system'),"")

    # Extract message history
    message_history = []
    for msg in inputs:
        if msg['type'] in ['human','ai']:
            message_history.append({
                "role": "user" if msg['type'] == 'human' else 'assistant',
                "content": msg['data']['content']
            })

    # Extract latest user message and model output
    latest_user_message = message_history[-1]['content'] if message_history else ""
    model_output = outputs['data']['content']

    evaluation_prompt = f"""
    System Prompt: {system_prompt}
    Message History: {json.dumps(message_history, indent=2)}
    Latest User Message: {latest_user_message}
    Model Output: {model_output}

    Based on the above information, evaluate the model's accuracy in ranking the list of products based on overall price and quality.
    where 0 indicates that the model completely mixed up the rannking of the products and 10 indicates that the model ranked the products in the correct order.
    Evaluate the model output based on the following criteria:
    - Ranking of products based on price and rating
    - Ranking of products based on the users needs
    - Ranking of products based on features provided for the price

    Respond with the score and a brief explanation for the score in the following JSON format:
    {{
        "score": <int>,
        "reason": <str>
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system", "content": "You are an AI assistant tasked with evaluating the accuracy of the model's output based on the given prompts and conversation context."},
            {"role":"user", "content": evaluation_prompt}
        ],
        response_format={
            "type": "json_object"
        },
        temperature=0.2
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return {
            "key": "product_ranking",
            "score": result["score"]/10,
            "reason": result["reason"]
        }
    except json.JSONDecodeError:
        return {
            "key": "product_ranking",
            "score": 0,
            "reason": "Failed to parse the evaluators response"
        }


@traceable
def prompt_compliance_evaluator(run: Run, example: Example) -> dict:
    inputs = example.inputs['input']
    outputs = example.outputs['output']
    # print("Inputs: ", inputs)
    #print("Outputs: ", outputs)

    system_prompt = next((msg['data']['content'] for msg in inputs if msg['type'] == 'system'),"")

    # Extract message history
    message_history = []
    for msg in inputs:
        if msg['type'] in ['human','ai']:
            message_history.append({
                "role": "user" if msg['type'] == 'human' else 'assistant',
                "content": msg['data']['content']
            })

    # Extract latest user message and model output
    latest_user_message = message_history[-1]['content'] if message_history else ""
    model_output = outputs['data']['content']

    evaluation_prompt = f"""
    System Prompt: {system_prompt}
    Message History: {json.dumps(message_history, indent=2)}
    Latest User Message: {latest_user_message}
    Model Output: {model_output}

    Based on the above information, evaluate the model's accuracy in summarizing the products to the user accurately according the system prompt and 
    suggest a score between 0 and 10, where 0 indicates that the model ignored the prompt and didn't do a good job summarizing the data for the user 
    and 10 indicates that the model did a great job summarizing the data for the user.
    Evaluate the model output based on the following criteria:
    - Does the output comply with the system prompt?
    - Does the output address the latest user message?
    - Is the output contain relevant and not repetitive information for the user?

    Respond with the score and a brief explanation for the score in the following JSON format:
    {{
        "score": <int>,
        "reason": <str>
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system", "content": "You are an AI assistant tasked with evaluating the accuracy of the model's output based on the given prompts and conversation context."},
            {"role":"user", "content": evaluation_prompt}
        ],
        response_format={
            "type": "json_object"
        },
        temperature=0.2
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return {
            "key": "prompt_compliance",
            "score": result["score"]/10,
            "reason": result["reason"]
        }
    except json.JSONDecodeError:
        return {
            "key": "prompt_compliance",
            "score": 0,
            "reason": "Failed to parse the evaluators response"
        }


data = "Consumer-Research-Summarizer"
experiment_prefix = "consumer-research-summarizer"
evaluators = [prompt_compliance_evaluator, product_ranking_evaluator]

results = evaluate(
    lambda inputs: inputs,
    data=data,
    evaluators=evaluators,
    experiment_prefix=experiment_prefix,
)

print(results)
