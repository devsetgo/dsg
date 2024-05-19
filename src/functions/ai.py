# -*- coding: utf-8 -*-
import ast
import re

from openai import AsyncOpenAI
from src.settings import settings
from loguru import logger

client = AsyncOpenAI(
    # This is the default and can be omitted
    api_key=settings.openai_key.get_secret_value(),
)

mood_analysis = [mood[0] for mood in settings.mood_analysis_weights]

timeout = 10
temperature = 0.2


async def get_analysis(content: str, mood_process: str = None) -> dict:
    logger.info("Starting get_analysis function")
    tags = await get_tags(content=content)
    summary = await get_summary(content=content,sentenace_length=1)
    mood_analysis = await get_mood_analysis(content=content,)
    mood = None
    if mood_process not in ["postive", "negative", "neutral"]:
        mood = await get_mood(content=content)
        mood_analysis = mood.get("mood")
        logger.info("processing mood")
    data = {
        "tags": tags,
        "summary": summary,
        "mood_analysis": mood_analysis,
        "mood": mood,
    }
    logger.info("openai request completed")
    logger.critical(f"analysis: {data}")
    logger.info("Finished get_analysis function")
    return data



async def get_tags(content: str, temperature: float = temperature,keyword_limit: int = 3) -> dict:
    logger.info("Starting get_tags function")
    prompt = f"For the following text create a python style list between 1 to {keyword_limit} 'one word' keywords to be stored as a python list and cannot be a persons name: {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": 'system',
                "content": prompt,
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content
    logger.critical(f"tag response: {response_content}")
    # Use a regular expression to extract a list from the response
    match = re.search(r"\[.*\]", response_content)
    if match:
        response_content = match.group(0)
    else:
        logger.error(
            f"Error: Unable to extract a list from response_content: {response_content}"
        )
        response_content = "[]"

    # Convert string representation of list to list
    try:
        response_content = ast.literal_eval(response_content)
    except SyntaxError:
        logger.error(f"Error: Unable to parse response_content: {response_content}")
        response_content = []

    # Remove any numbers or symbols from the items in the list
    response_content = [
        "".join(re.findall("[a-zA-Z]+", item)) for item in response_content
    ]

    # Store the keywords in a dictionary
    response_dict = {"tags": response_content}
    logger.info("Finished get_tags function")
    return response_dict


async def get_summary(content: str, temperature: float = temperature, sentenace_length:int=1) -> dict:
    logger.info("Starting get_summary function")
    prompt = f"Please summarize the following text that is {sentenace_length} sentenance in length and no longer than 500 characters max and cannot contain any persons name: {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": 'system',
                "content": prompt,
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content
    logger.critical(f"summary content: {response_content}")
    # Store the summary in a dictionary
    response_dict = response_content
    logger.info("Finished get_summary function")
    return response_dict

async def get_mood_analysis(content: str, temperature: float = temperature) -> dict:
    logger.info("Starting get_mood_analysis function")
    # prompt = f"Please analyze the mood of the following text and provide a single word to describe the content: {content}"
    prompt = f"For the following text provide a single word response - like 'happy', 'sad', 'frustrated', 'perplexed' - that expresses the mood content"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": 'system',
                "content": prompt,
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content
    logger.critical(f"mood analysis content: {response_content}")
    # Store the mood analysis in a dictionary
    response_dict = {"mood_analysis": response_content}
    logger.info("Finished get_mood_analysis function")
    return response_dict

async def get_mood(content: str, temperature: float = temperature) -> dict:
    moods:list = ['positive','negative','neutral']
    logger.info("Starting get_mood function")
    prompt = f"Please determine the mood of the following text using only one of these moods {moods} for the content: {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": 'system',
                "content": prompt,
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content

    # Store the mood in a dictionary
    response_dict = {"mood": response_content}
    logger.critical(f"mood content: {response_content}")
    logger.info("Finished get_mood function")
    return response_dict

async def analyze_post(content: str, temperature: float = temperature) -> dict:
    logger.info("Starting analyze_post function")
    tags = await get_tags(content=content)
    summary = await get_summary(content=content, sentenace_length=2)
    mood_analysis = await get_mood_analysis(content=content)
    mood = await get_mood(content=content)
    data = {
        "tags": tags,
        "summary": summary,
        "mood_analysis": mood_analysis,
        "mood": mood,
    }
    logger.info("openai request completed")
    logger.critical(f"post analysis content: {data}")
    logger.info("Finished analyze_post function")
    return data
