# -*- coding: utf-8 -*-
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
    return ph.hash(password)


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


def check_needs_rehash(hash: str) -> bool:
    """
    Check if a hash needs to be rehashed.

    :param hash: The hash to check.
    :return: True if the hash needs to be rehashed, False otherwise.
    """
    return ph.check_needs_rehash(hash)


# run through each function above for a quick test
if __name__ == "__main__":
    test_password = "test_password"
    hashed_password = hash_password(test_password)
    print(f"hashed_password: {hashed_password}")
    print(f"verify_password: {verify_password(hashed_password, test_password)}")
    print(f"check_needs_rehash: {check_needs_rehash(hashed_password)}")
