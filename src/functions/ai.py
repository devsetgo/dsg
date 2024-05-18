# -*- coding: utf-8 -*-
import ast
import re

from openai import AsyncOpenAI
from src.settings import settings

client = AsyncOpenAI(
    # This is the default and can be omitted
    api_key=settings.openai_key.get_secret_value(),
)

mood_analysis = [mood[0] for mood in settings.mood_analysis_weights]

timeout = 10
temperature = 0.2


async def get_analysis(content: str, mood_process: str = None) -> dict:
    tags = await get_tags(content=content)
    summary = await get_summary(content=content)
    mood_analysis = await get_mood_analysis(content=content)
    mood = None
    if mood_process not in ["postive", "negative", "neutral"]:
        mood = await get_mood(content=content)
        mood_analysis = mood.get("mood")
    data = {
        "tags": tags,
        "summary": summary,
        "mood_analysis": mood_analysis,
        "mood": mood,
    }
    return data


async def get_tags(content: str, temperature: float = temperature) -> dict:
    keyword_limit: int = 3
    prompt = f"For the following text create a python style list between 1 to {keyword_limit} 'one word' keywords to be stored as a python list and cannot be a persons name: {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content

    # Use a regular expression to extract a list from the response
    match = re.search(r"\[.*\]", response_content)
    if match:
        response_content = match.group(0)
    else:
        print(
            f"Error: Unable to extract a list from response_content: {response_content}"
        )
        response_content = "[]"

    # Convert string representation of list to list
    try:
        response_content = ast.literal_eval(response_content)
    except SyntaxError:
        print(f"Error: Unable to parse response_content: {response_content}")
        response_content = []

    # Remove any numbers or symbols from the items in the list
    response_content = [
        "".join(re.findall("[a-zA-Z]+", item)) for item in response_content
    ]

    # Store the keywords in a dictionary
    response_dict = {"tags": response_content}
    return response_dict


async def get_summary(content: str, sentance_length: int = 1, temperature: float = temperature) -> dict:

    prompt = f"Provide a short summary that is no more than {sentance_length} sentence description or a max of 500 characters. It cannot contain names of people: {content}"
    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )
    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content

    return response_content


async def get_mood_analysis(content: str, temperature: float = temperature) -> dict:
    # prompt = f"Please analyze the following text and tell me what overall mood it expresses in a single word: {content}"
    prompt = f"In a single word describe the overall mood of this: {content}"
    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )
    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content
    return response_content


async def get_mood(content: str, temperature: float = temperature) -> dict:
    mood_choices = ["positive", "negative", "neutral"]
    prompt = f"Please analyze the following text and tell me what mood choice {str(mood_choices)} it expresses: {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )

    # Extract the content from the response and return it as {'mood': response}
    response_content = chat_completion.choices[0].message.content
    # Set the default mood as 'neutral'
    mood = "neutral"
    # extract the first word in the response that matches one the mood_choices
    for mood_choice in mood_choices:
        if mood_choice in response_content:
            mood = mood_choice
            break

    return {"mood": mood}


#### Analyze posts
async def analyze_post(content: str) -> dict:
    tags = await get_tags(content=content)
    summary = await get_summary(content=content)
    return {"tags": tags, "summary": summary}
