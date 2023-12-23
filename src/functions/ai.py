# -*- coding: utf-8 -*-

from openai import AsyncOpenAI

from src.settings import settings

client = AsyncOpenAI(
    # This is the default and can be omitted
    api_key=settings.openai_key,
)


async def get_tags(content: str) -> dict:
    prompt = f"Please analyze the following text and provide no more than 3 one-word psychological keyword tags that best capture its essence: {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        # response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that will provide no more than 3 one-word psychological keyword tags that best capture its essence.",
            },
            {"role": "user", "content": content},
        ],
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content

    # Split the content into a list of keywords
    keywords = response_content.split(", ")

    # Store the keywords in a dictionary
    response_dict = {"tags": keywords}
    return response_dict


async def get_summary(content: str) -> dict:
    prompt = f"Please analyze the following text and provide a very short description (less than 10 words) in the format of 'feeling blank': {content}"

    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        # response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that will provide a very short description (less than 10 words) in the format of 'feeling blank'.",
            },
            {"role": "user", "content": content},
        ],
    )

    # Extract the content from the response
    response_content = chat_completion.choices[0].message.content

    # Split the content into a list of keywords
    keywords = response_content.split(", ")

    # Store the keywords in a dictionary
    response_dict = {"tags": keywords}
    return response_content


import json


def open_json():
    with open("/workspaces/dsg/note.json") as read_file:
        # load file into data variable
        result = json.load(read_file)

    return result


def save_json(data):
    with open("/workspaces/dsg/new_note.json", "w") as outfile:
        json.dump(data, outfile)


async def run():
    big_list = open_json()
    # pick 5 random notes from the list
    print(len(big_list))
    import random

    content_list = random.sample(big_list, 5)
    # print(content_list)
    new_data = []
    for content in content_list:
        print(content["created_date"])
        summary = await get_summary(content=content["my_note"])
        print(summary)
        tags = await get_tags(content=content["my_note"])
        print(tags)
        new_data.append(
            {
                "created_date": content["created_date"],
                "my_note": content["my_note"],
                "summary": summary,
                "tags": tags,
            }
        )

    save_json(new_data)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
