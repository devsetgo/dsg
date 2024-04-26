# -*- coding: utf-8 -*-
"""
This module provides a function to validate email addresses. It uses the
`email_validator` library to check if an email address is valid and deliverable,
and logs the process using the `loguru` library.

The main function in this module is `validate_email_address`, which takes an
email address as input and returns a dictionary with information about the
validity of the email address, the normalized email address, and a dictionary
with additional information about the email address if it's valid.

Example:
    validate_email_address("test@example.com")

Attributes:
    resolver (caching_resolver): A caching resolver with a timeout of 5 seconds.

Functions:
    validate_email_address(email: str) -> str: Validates an email address and
        returns a dictionary with information about the email address.
"""

from email_validator import EmailNotValidError, caching_resolver, validate_email
from loguru import logger
import pytz

timezones = pytz.all_timezones


# Create a caching resolver with a timeout of 5 seconds
resolver = caching_resolver(timeout=5)


# Function to validate an email address
def validate_email_address(email: str) -> str:
    # Log the email being validated
    logger.info(f"Validating email: {email}")
    try:
        # Validate the email address, checking for deliverability
        emailinfo = validate_email(
            email, check_deliverability=True, dns_resolver=resolver
        )
        # Normalize the email address
        email = emailinfo.normalized

        # Initialize an empty dictionary to store email information
        email_dict = {}

        # Populate the dictionary with attributes from the validated email,
        # if they exist
        if hasattr(emailinfo, "normalized"):
            email_dict["email"] = emailinfo.normalized
        if hasattr(emailinfo, "local_part"):
            email_dict["local"] = emailinfo.local_part
        if hasattr(emailinfo, "domain"):
            email_dict["domain"] = emailinfo.domain
        if hasattr(emailinfo, "ascii_email"):
            email_dict["ascii_email"] = emailinfo.ascii_email
        if hasattr(emailinfo, "ascii_local_part"):
            email_dict["ascii_local"] = emailinfo.ascii_local_part
        if hasattr(emailinfo, "ascii_domain"):
            email_dict["ascii_domain"] = emailinfo.ascii_domain
        if hasattr(emailinfo, "smtputf8"):
            email_dict["smtputf8"] = emailinfo.smtputf8
        if hasattr(emailinfo, "domain_address"):
            email_dict["domain_address"] = emailinfo.domain_address
        if hasattr(emailinfo, "display_name"):
            email_dict["display_name"] = emailinfo.display_name
        if hasattr(emailinfo, "mx"):
            email_dict["mx"] = emailinfo.mx
        if hasattr(emailinfo, "mx_fallback_type"):
            email_dict["mx_fallback_type"] = emailinfo.mx_fallback_type
        if hasattr(emailinfo, "spf"):
            email_dict["spf"] = emailinfo.spf

        # Log that the email is valid
        logger.info(f"Email is valid: {email}")
        # Return a dictionary indicating that the email is valid, along with
        # the normalized email and the email information dictionary
        return {"valid": True, "email": email, "email_dict": email_dict}
    except EmailNotValidError as e:
        # Log the error if email validation fails
        logger.error(f"Email validation failed for {email}: {str(e)}")
        # Return a dictionary indicating that the email is not valid, along
        # with the original email and the error message
        return {"valid": False, "email": email, "error": str(e)}


if __name__ == "__main__":
    # create a list of email addresses to check if valid
    email_addresses = [
        "bob@devsetgo.com",
        "bob@devset.go",
        "foo@yahoo.com",
        "bob@gmail.com",
        "very fake@devsetgo.com",
        "jane.doe@example.com",
        "john_doe@example.co.uk",
        "user.name+tag+sorting@example.com",
        "x@example.com",  # shortest possible email address
        "example-indeed@strange-example.com",
        "admin@mailserver1",  # local domain name with no TLD
        "example@s.example",  # see the list of Internet top-level domains
        '" "@example.org',  # space between the quotes
        '"john..doe"@example.org',  # quoted double dot
        "mailhost!username@example.org",  # bangified host route used for uucp mailers
        "user%example.com@example.org",  # percent sign in local part
        "user-@example.org",  # valid due to the last character being an allowed character
        # Invalid email addresses
        "Abc.example.com",  # no @ character
        "A@b@c@example.com",  # only one @ is allowed outside quotation marks
        'a"b(c)d,e:f;g<h>i[j\\k]l@example.com',  # none of the special characters in this local part are allowed outside quotation marks
        'just"not"right@example.com',  # quoted strings must be dot separated or the only element making up the local-part
        'this is"not\\allowed@example.com',  # spaces, quotes, and backslashes may only exist when within quoted strings and preceded by a backslash
        'this\\ still\\"not\\\\allowed@example.com',  # even if escaped (preceded by a backslash), spaces, quotes, and backslashes must still be contained by quotes
        "1234567890123456789012345678901234567890123456789012345678901234+x@example.com",  # local part is longer than 64 characters
    ]

    import pprint
    import time

    for email in email_addresses:
        t0 = time.time()
        res = validate_email_address(email)
        if res["valid"]:

            pprint.pprint(res, indent=4)
            print(f"Time taken: {time.time() - t0:.2f}")

    for tz in timezones:
        print(tz)
