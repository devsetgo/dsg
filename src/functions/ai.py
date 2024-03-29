# -*- coding: utf-8 -*-

from openai import AsyncOpenAI

from src.settings import settings

client = AsyncOpenAI(
    # This is the default and can be omitted
    api_key=settings.openai_key.get_secret_value(),
)

mood_analysis: list = [
    "ecstatic",
    "joyful",
    "happy",
    "pleased",
    "content",
    "concerned",
    "neutral",
    "indifferent",
    "disappointed",
    "sad",
    "upset",
    "angry",
    "furious",
]


async def get_analysis(content: str) -> dict:

    tags = await get_tags(content=content)
    summary = await get_summary(content=content)
    mood_analysis = await get_mood_analysis(content=content)
    return {"tags": tags, "summary": summary, "mood_analysis": mood_analysis}


async def get_tags(content: str) -> dict:
    keyword_limit: int = 2
    # prompt = f"Please analyze the following text and provide one-word psychological keywords capture its essence: {content}"
    prompt = f"Please analyze the following text and provide 'one-word' keywords capture its essence: {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        # response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": f"You are a helpful assistant that will provide no more than {keyword_limit} 'one-word' keyword to be used as tags.",
            },
            {"role": "user", "content": content},
        ],
        temperature=0.2,  # Adjust the temperature here
    )
    # print(chat_completion)
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
        temperature=0.2,  # Adjust the temperature here
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
        temperature=0.2,  # Adjust the temperature here
    )
    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content
    return response_content


# import json


# def open_json():
#     with open("/workspaces/dsg/note.json") as read_file:
#         # load file into data variable
#         result = json.load(read_file)

#     return result


# def save_json(data):
#     with open("/workspaces/dsg/new_note.json", "w") as outfile:
#         json.dump(data, outfile)


# async def run():
#     big_list = open_json()
#     # pick 5 random notes from the list

#     import random

#     content_list = random.sample(big_list, 5)

#     new_data = []
#     for content in content_list:

#         summary = await get_summary(content=content["my_note"])

#         tags = await get_tags(content=content["my_note"])

#         new_data.append(
#             {
#                 "created_date": content["created_date"],
#                 "my_note": content["my_note"],
#                 "summary": summary,
#                 "tags": tags,
#             }
#         )

#     save_json(new_data)


# if __name__ == "__main__":
#     import asyncio

#     # asyncio.run(run())
#     content = """
#     Sell Mom's house to Kelly Thursday/Friday. I am sure Kristi will lose her mind over something to make it a miserable experience.

#     Kristi is a psychopath and Kelly isn't very appreciative. If it wasn't for me, they would both have gained nothing. But of course no good deed goes unpunished.
#     """
#     asyncio.run(get_analysis(content=content))
