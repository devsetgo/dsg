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
    3 July, 2024
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
    try:
        text_bytes = text.encode('utf-8')
        encrypted_bytes = pipe.encrypt(text_bytes)
        logger.info("Text encrypted successfully.")
        return encrypted_bytes
    except Exception as e:
        error:str = f"Encryption failed: {e}"
        logger.error(error)
        return error

def decrypt_text(text: bytes) -> str:
    try:
        decrypted_bytes = pipe.decrypt(text)
        decrypted_text = decrypted_bytes.decode('utf-8')
        logger.info("Text decrypted successfully.")
        return decrypted_text
    except Exception as e:
        error:str = f"Decryption failed: {e}"
        logger.error(error)
        return error  # Or handle the error as appropriate

