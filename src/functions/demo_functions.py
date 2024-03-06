# -*- coding: utf-8 -*-
import random
from loguru import logger


def get_pypi_demo_list(max_range=20):

    logger.info("Starting to generate demo list.")

    # open csv file located at src/endpoints/demo.csv
    with open("src/endpoints/demo.csv", "r") as file:
        # read the file
        data = file.read()
        # split the data into a list
        data = data.split("\n")
        # remove empty strings from the list
        data = [x for x in data if x != ""]
        # get a random list of x items from the list
        data_sample = random.randint(1, max_range)
        logger.info(f"Generated {data_sample} random items.")
        # create a weight list that gives higher probability to the more popular libraries
        weights = [x for x in range(len(data), 0, -1)]
        data = random.choices(data, weights=weights, k=data_sample)
        # known vulnerability to the data
        vulnerbilities = ["py", "pycrypto", "ecdsa", "onnx"]
        for v in vulnerbilities:
            data.append(v)

        # join the list into a string with each item on a new line
        data = "\n".join(data)
        logger.info("Finished generating demo list.")

        # return the formatted data
        return data


def get_note_demo_paragraph(length=10):
    import silly
    logger.info("Starting to generate demo paragraph.")
    data = silly.paragraph(length=length)
    # make the output a total of 19999 characters by looping data variable until it reaches 19999 characters
    while len(data) < 19999:
        data += data
    logger.info("Finished generating demo paragraph.")
    data = data[:19999]
    return data