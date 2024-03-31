# -*- coding: utf-8 -*-

from openai import AsyncOpenAI

from src.settings import settings

client = AsyncOpenAI(
    # This is the default and can be omitted
    api_key=settings.openai_key.get_secret_value(),
)

mood_analysis = [mood[0] for mood in settings.mood_analysis_weights]

timeout = 10
temperature = 0.2


async def get_analysis(content: str) -> dict:

    tags = await get_tags(content=content)
    summary = await get_summary(content=content)
    mood_analysis = await get_mood_analysis(content=content)
    return {"tags": tags, "summary": summary, "mood_analysis": mood_analysis}


async def get_tags(content: str) -> dict:
    keyword_limit: int = 4
    # prompt = f"Please analyze the following text and provide one-word psychological keywords capture its essence: {content}"
    prompt = f"Please analyze the following text and provide 'one-word' keywords capture its essence: {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        # response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": f"You are a helpful assistant that will provide no more than {keyword_limit} 'one-word' keyword to be used as tags. Names of people cannot be included.",
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,  # Adjust the temperature here
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content

    # Split the content into a list of keywords
    keywords = response_content.split(", ")

    # Store the keywords in a dictionary
    response_dict = {"tags": keywords}
    return response_dict


async def get_summary(content: str) -> dict:
    summary_length: int = 5
    # prompt = f"Please analyze the following text and provide a very short description (less than 10 words) in the format of 'feeling blank': {content}"
    prompt = f"Please analyze the following text and provide a short description and without naming a person in the summary: {content}"
    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": f"You are a helpful assistant that will provide a short desciption without naming a person and focusing on the sentiments expressed in less than {summary_length} words.",
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,  # Adjust the temperature here
    )
    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content
    return response_content


async def get_mood_analysis(content: str) -> dict:

    # prompt = f"Please analyze the following text and provide a very short description (less than 10 words) in the format of 'feeling blank': {content}"
    prompt = f"Please analyze the following text and tell me what overall mood it expresses in a single word: {content}"
    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": f"You are a helpful assistant that will pick the mood from these options {str(mood_analysis)} as the overall feeling and return as a single word.",
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,  # Adjust the temperature here
    )
    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content
    return response_content


async def get_mood(content: str) -> dict:
    mood_choices = ["positive", "negative", "neutral"]
    prompt = f"Please analyze the following text and tell me what mood choice {str(mood_choices)} it expresses: {content}"
    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": f"You are a helpful assistant that will pick the mood from only these options {str(mood_choices)} and return that word.",
            },
            {"role": "user", "content": content},
        ],
        temperature=temperature,  # Adjust the temperature here
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
