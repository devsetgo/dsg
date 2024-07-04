# -*- coding: utf-8 -*-
"""
Module for encrypting and decrypting text using Fernet symmetric encryption.

This module provides functionality to encrypt and decrypt text strings. It uses
Fernet symmetric encryption, which ensures that data encrypted using a key can
only be decrypted using the same key. The key is derived from a passphrase
using PBKDF2 HMAC SHA-256, and then encoded to a URL-safe base64 format.

Functions:
    encrypt_text(text: str) -> bytes: Encrypts a text string into bytes.
    decrypt_text(text: bytes) -> str: Decrypts bytes back into a text string.

Author:
    Mike Ryan
    MIT Licensed
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from loguru import logger

from ..settings import settings


class EncryptionError(Exception):
    """Exception raised for errors during the encryption process."""

class DecryptionError(Exception):
    """Exception raised for errors during the decryption process."""


# Original phrase
phrase: bytes = settings.phrase.get_secret_value().encode('utf-8')
# Generate a 32-byte key using PBKDF2 HMAC SHA-256
key: bytes = hashlib.pbkdf2_hmac('sha256', phrase, b'salt', 100000)
# Encode the key to make it url-safe base64-encoded
encoded_key: bytes = base64.urlsafe_b64encode(key)
pipe: Fernet = Fernet(key=encoded_key)  # Corrected to use encoded_key

def encrypt_text(text: str) -> bytes:
    """
    Encrypts a text string into bytes using Fernet symmetric encryption.

    Args:
        text (str): The text string to be encrypted.

    Returns:
        bytes: The encrypted text as bytes. If an error occurs, the function
        will log the error and return the error message as a string instead.

    Raises:
        EncryptionError: If an error occurs during the encryption process.

    This function converts the input text string into bytes, then encrypts
    these bytes using the Fernet symmetric encryption scheme. It logs the
    operation's success or failure. In case of an exception, it raises an
    EncryptionError with the error message.
    """
    try:
        text_bytes = text.encode('utf-8')  # Convert the input text to bytes
        encrypted_bytes = pipe.encrypt(text_bytes)  # Encrypt the bytes
        logger.debug("Text encrypted successfully.")
        return encrypted_bytes
    except Exception as e:
        error = f"Encryption failed: {e}"
        logger.error(error)
        raise EncryptionError(error)  # Raise an EncryptionError with the error message

def decrypt_text(text: bytes) -> str:
    """
    Decrypts bytes back into a text string using Fernet symmetric encryption.

    Args:
        text (bytes): The encrypted text as bytes to be decrypted.

    Returns:
        str: The decrypted text string. If an error occurs, the function will
        log the error and return the error message as a string instead.

    Raises:
        DecryptionError: If an error occurs during the decryption process.

    This function decrypts the input bytes using the Fernet symmetric encryption
    scheme and converts the decrypted bytes back into a string. It logs the
    operation's success or failure. In case of an exception, it raises a
    DecryptionError with the error message.
    """
    try:
        decrypted_bytes = pipe.decrypt(text)  # Decrypt the input bytes
        decrypted_text = decrypted_bytes.decode('utf-8')  # Convert decrypted bytes back to string
        logger.debug("Text decrypted successfully.")
        return decrypted_text
    except Exception as e:
        error = f"Decryption failed: {e}"
        logger.error(error)
        raise DecryptionError(error)  # Raise a DecryptionError with the error message
