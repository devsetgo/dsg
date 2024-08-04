# -*- coding: utf-8 -*-
"""
This module provides functions for hashing passwords using the Argon2 algorithm.

It includes the following functions:
- `hash_password(password: str) -> str`: Hashes a password.
- `verify_password(hash: str, password: str) -> bool`: Verifies a password against a hash.
- `check_needs_rehash(hash: str) -> bool`: Checks if a hash needs to be rehashed.

The module uses the `argon2` library to perform the hashing. The `PasswordHasher` object is configured with the following parameters:
- `time_cost=3`: The time cost factor.
- `memory_cost=65536`: The memory cost factor.
- `parallelism=4`: The degree of parallelism.
- `hash_len=32`: The length of the hash.
- `salt_len=16`: The length of the salt.
- `encoding="utf-8"`: The encoding to use.

If run as a script, the module will hash a test password, verify it against the hash, and check if the hash needs to be rehashed.

Author:
    Mike Ryan
    MIT Licensed
"""

from argon2 import PasswordHasher, exceptions
from loguru import logger

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    encoding="utf-8",
)


def hash_password(password: str) -> str:
    """
    Hash a password using the Argon2 algorithm.

    :param password: The password to hash.
    :return: The hashed password.
    """
    try:
        return ph.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        return None


def verify_password(hash: str, password: str) -> bool:
    """
    Verify a password against a hash.

    :param hash: The hash to verify against.
    :param password: The password to verify.
    :return: True if the password matches the hash, False otherwise.
    """
    try:
        ph.verify(hash, password)
        return True
    except exceptions.VerifyMismatchError:
        return False
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def check_needs_rehash(hash: str) -> bool:
    """
    Check if a hash needs to be rehashed.

    :param hash: The hash to check.
    :return: True if the hash needs to be rehashed, False otherwise.
    """
    try:
        return ph.check_needs_rehash(hash)
    except Exception as e:
        logger.error(f"Error checking if hash needs rehash: {e}")
        return False


config = {
    "min_length": 8,
    "min_digits": 2,
    "min_uppercase": 2,
    "min_lowercase": 2,
    "symbols": [
        "!",
        "@",
        "#",
        "$",
        "%",
        "^",
        "&",
        "*",
        "(",
        ")",
        "<",
        ">",
        "?",
        "|",
        "~",
    ],
    "min_symbols": 1,
}


def check_password_complexity(password):
    if len(password) < config.get("min_length", 0):
        return "Password is too short"

    if sum(c.isdigit() for c in password) < config.get("min_digits", 0):
        return "Password does not have enough digits"

    if sum(c.isupper() for c in password) < config.get("min_uppercase", 0):
        return "Password does not have enough uppercase letters"

    if sum(c.islower() for c in password) < config.get("min_lowercase", 0):
        return "Password does not have enough lowercase letters"

    # Check for disallowed symbols
    allowed_characters = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        + "".join(config.get("symbols", []))
    )
    if not set(password).issubset(allowed_characters):
        return "Password contains disallowed characters"

    return True


# run through each function above for a quick test
if __name__ == "__main__":
    test_password = "test_password"
    hashed_password = hash_password(test_password)
    print(f"hashed_password: {hashed_password}")
    print(f"verify_password: {verify_password(hashed_password, test_password)}")
    print(f"check_needs_rehash: {check_needs_rehash(hashed_password)}")
    print(check_password_complexity(test_password, config))  # True
