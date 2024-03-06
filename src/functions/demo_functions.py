# -*- coding: utf-8 -*-
"""
This module contains two functions for generating demo data.

`get_pypi_demo_list(max_range=20)` generates a list of Python libraries, with a
bias towards more popular libraries. It reads the library names from a CSV file,
selects a random number of libraries from the file, and appends some known
vulnerabilities to the list. The list is then returned as a string, with each
library on a new line.

Args:
    max_range (int, optional): The maximum number of libraries to select from
    the CSV file. Defaults to 20.

Returns:
    str: A string containing the selected library names, each on a new line.

`get_note_demo_paragraph(length=10, max_length=19999)` generates a random
paragraph of text using the `silly` library. The `length` parameter determines
the number of sentences in the paragraph. The `max_length` parameter limits the
number of characters in the returned string. If the generated paragraph is
longer than `max_length`, it will be truncated. If it's shorter, the entire
paragraph will be returned.

Args:
    length (int, optional): The number of sentences in the paragraph. Defaults
    to 10. max_length (int, optional): The maximum number of characters in the
    returned string. Defaults to 19999.

Returns:
    str: A string containing the generated paragraph.
"""
import random
from loguru import logger


def get_pypi_demo_list(max_range=20):
    # Log the start of the list generation
    logger.info("Starting to generate demo list.")

    # Open the CSV file located at src/endpoints/demo.csv
    with open("src/endpoints/demo.csv", "r") as file:
        # Read the file
        data = file.read()
        # Split the data into a list where each line of the file becomes a
        # separate element
        data = data.split("\n")
        # Remove empty strings from the list
        data = [x for x in data if x != ""]
        # Get a random number between 1 and max_range
        data_sample = random.randint(1, max_range)
        logger.info(f"Generated {data_sample} random items.")
        # Create a weight list that gives higher probability to the more popular
        # libraries
        weights = [x for x in range(len(data), 0, -1)]
        # Select data_sample number of elements from data list with the given
        # weights
        data = random.choices(data, weights=weights, k=data_sample)
        # Known vulnerabilities to the data
        vulnerbilities = ["py", "pycrypto", "ecdsa", "onnx"]
        # Append each vulnerability to the data list
        for v in vulnerbilities:
            data.append(v)

        # Join the list into a string with each item on a new line
        data = "\n".join(data)
        logger.info("Finished generating demo list.")

        # Return the formatted data
        return data


def get_note_demo_paragraph(length=10, max_length=19999):
    # Import the silly library, which is used to generate random text
    import silly

    # Log the start of the paragraph generation
    logger.info("Starting to generate demo paragraph.")

    # Generate a random paragraph with the specified length The length parameter
    # determines the number of sentences in the paragraph
    data = silly.paragraph(length=length)

    # Return the paragraph, but limit its length to max_length characters If the
    # generated paragraph is longer than max_length, it will be truncated If
    # it's shorter, the entire paragraph will be returned
    return data[:max_length]
