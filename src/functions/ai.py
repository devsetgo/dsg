# -*- coding: utf-8 -*-
"""
This module contains functions for interacting with the OpenAI API.

It uses the AsyncOpenAI client to make asynchronous requests to the API. The module includes functions for getting tags, summary, mood analysis, and mood from a given content.

Functions:
    get_analysis(content: str, mood_process: str = None) -> dict: Gets the tags, summary, mood analysis, and mood from the given content.

"""
import ast
import re
from functools import lru_cache
from typing import Dict, List

import spacy
from loguru import logger
from openai import AsyncOpenAI
from spacy.language import Language

from src.settings import settings

client = AsyncOpenAI(
    # This is the default and can be omitted
    api_key=settings.openai_key.get_secret_value(),
)

mood_analysis = [mood[0] for mood in settings.mood_analysis_weights]

timeout = 10
temperature = 0.2


async def get_analysis(content: str, mood_process: str = None) -> dict:
    """
    Gets the tags, summary, mood analysis, and mood from the given content.

    Args:
        content (str): The content to analyze.
        mood_process (str, optional): The mood process. Defaults to None.

    Returns:
        dict: A dictionary containing the tags, summary, mood analysis, and mood.
    """
    logger.info("Starting get_analysis function")

    # Get the tags from the content
    tags = await get_tags(content=content)

    # Get the summary from the content
    summary = await get_summary(content=content, sentence_length=1)

    # Get the mood analysis from the content
    mood_analysis = await get_mood_analysis(content=content)

    mood = None
    # If the mood process is not one of the expected values, get the mood from the content
    if mood_process not in ["postive", "negative", "neutral"]:
        mood = await get_mood(content=content)
        logger.info("processing mood")

    # Create a dictionary with the analysis results
    data = {
        "tags": tags,
        "summary": summary,
        "mood_analysis": mood_analysis["mood_analysis"],
        "mood": mood,
    }

    logger.info("openai request completed")
    logger.debug(f"analysis: {data}")
    logger.info("Finished get_analysis function")

    return data


async def get_tags(
    content: str, temperature: float = temperature, keyword_limit: int = 3
) -> dict:
    """
    Gets a list of keywords from the given content.

    Args:
        content (str): The content to analyze.
        temperature (float, optional): The temperature to use for the OpenAI API. Defaults to temperature.
        keyword_limit (int, optional): The maximum number of keywords to return. Defaults to 3.

    Returns:
        dict: A dictionary containing the keywords.
    """
    logger.info("Starting get_tags function")

    # Create the prompt for the OpenAI API
    prompt = f"For the following text create a python style list between 1 to {keyword_limit} 'one word' keywords to be stored as a python list and cannot be a persons name: {content}"

    # Send the prompt to the OpenAI API
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
    logger.debug(f"tag response: {response_content}")

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
    logger.debug(f"tag content {response_content}")
    response_dict = {"tags": response_content}
    logger.info("Finished get_tags function")
    resp = tag_check(response_dict)
    return resp



@lru_cache(maxsize=128)
def load_model() -> Language:
    """
    Load and cache the multi-language spaCy model to improve performance.

    Returns:
        The loaded spaCy Language model.
    """
    # Load the multi-language model
    nlp = spacy.load("xx_ent_wiki_sm")
    return nlp

def tag_check(tags: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Filter out tags that are recognized as person names by the spaCy model.

    Args:
        tags: A dictionary with a key "tags" containing a list of strings to be checked.

    Returns:
        A dictionary with the key "tags" containing a filtered list of strings
        where any recognized person names have been removed.
    """
    # Load the multi-language model
    nlp = load_model()
    tag_list = tags["tags"]
    filtered_tags = []
    for tag in tag_list:
        # Process each tag through the spaCy model
        doc = nlp(tag)
        # Filter out tags recognized as person names ("PER")
        if not any(ent.label_ == "PER" for ent in doc.ents):
            filtered_tags.append(tag)
    return {'tags': filtered_tags}

async def get_summary(
    content: str, temperature: float = temperature, sentence_length: int = 1
) -> dict:
    """
    Gets a summary of the given content.

    Args:
        content (str): The content to summarize.
        temperature (float, optional): The temperature to use for the OpenAI API. Defaults to temperature.
        sentence_length (int, optional): The length of the summary in sentences. Defaults to 1.

    Returns:
        dict: A dictionary containing the summary.
    """
    logger.info("Starting get_summary function")

    # Create the prompt for the OpenAI API
    prompt = f"Please summarize the content and provide {sentence_length} concise sentence in length as a title and it cannot contain any persons name"

    # Send the prompt to the OpenAI API
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
    logger.debug(f"summary content: {response_content}")

    # Store the summary in a dictionary
    response_dict = response_content
    logger.info("Finished get_summary function")

    return response_dict


async def get_mood_analysis(content: str, temperature: float = temperature) -> dict:
    """
    Analyzes the mood of the given content.

    Args:
        content (str): The content to analyze.
        temperature (float, optional): The temperature to use for the OpenAI API. Defaults to temperature.

    Returns:
        dict: A dictionary containing the mood analysis.
    """
    logger.info("Starting get_mood_analysis function")
    moods = [mood[0] for mood in settings.mood_analysis_weights]
    # Create the prompt for the OpenAI API
    prompt = f"For the following text provide a single expressive word response that expresses the general mood of the content from these options {moods}. It will be stored in a python variable with a max character length of 25."

    # Send the prompt to the OpenAI API
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
    logger.debug(f"mood analysis content: {response_content}")

    # Store the mood analysis in a dictionary
    response_dict = {"mood_analysis": response_content}
    logger.info("Finished get_mood_analysis function")

    return response_dict


async def get_mood(content: str, temperature: float = temperature) -> dict:
    """
    Determines the mood of the given content.

    Args:
        content (str): The content to analyze.
        temperature (float, optional): The temperature to use for the OpenAI API. Defaults to temperature.

    Returns:
        dict: A dictionary containing the mood.
    """
    # Define the possible moods
    moods: list = ["positive", "negative", "neutral"]
    logger.info("Starting get_mood function")

    # Create the prompt for the OpenAI API
    prompt = f"Please determine the mood of the following text using only one of these moods {moods} for the content. It will be stored in a python variable with a max character length of 25."

    # Send the prompt to the OpenAI API
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
    logger.debug(f"mood content: {response_content}")

    # Store the mood in a dictionary
    response_dict = {"mood": response_content}

    logger.info("Finished get_mood function")

    return response_dict


async def analyze_post(content: str, temperature: float = temperature) -> dict:
    """
    Analyzes a post and returns tags, summary, mood analysis, and mood.

    Args:
        content (str): The content to analyze.
        temperature (float, optional): The temperature to use for the OpenAI API. Defaults to temperature.

    Returns:
        dict: A dictionary containing the tags, summary, mood analysis, and mood.
    """
    logger.info("Starting analyze_post function")

    # Get the tags from the content
    tags = await get_tags(content=content)

    # Get a two-sentence summary of the content
    summary = await get_summary(content=content, sentence_length=2)

    # Analyze the mood of the content
    mood_analysis = await get_mood_analysis(content=content)

    # Determine the mood of the content
    mood = await get_mood(content=content)

    # Store the analysis results in a dictionary
    data = {
        "tags": tags,
        "summary": summary,
        "mood_analysis": mood_analysis,
        "mood": mood,
    }

    logger.info("openai request completed")
    logger.debug(f"post analysis content: {data}")
    logger.info("Finished analyze_post function")

    return data


async def get_url_summary(
    url: str, temperature: float = temperature, sentence_length: int = 2
) -> dict:
    """
    Gets a summary of the given url.

    Args:
        url (str): The url to summarize.
        temperature (float, optional): The temperature to use for the OpenAI API. Defaults to temperature.
        sentence_length (int, optional): The length of the summary in sentences. Defaults to 1.

    Returns:
        dict: A dictionary containing the summary.
    """
    logger.info("Starting get_url_summary function")

    # Create the prompt for the OpenAI API
    prompt = f"Please summarize the url and provide {sentence_length} concise sentence in length as a summary for the URL"

    # Send the prompt to the OpenAI API
    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {"role": "user", "content": url},
        ],
        temperature=temperature,
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content
    logger.debug(f"summary content: {response_content}")

    # Store the summary in a dictionary
    response_dict = response_content
    logger.info("Finished get_url_summary function")

    return response_dict
