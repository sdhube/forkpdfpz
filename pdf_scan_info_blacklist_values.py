import re

# Compiled once upon module import
BLACKLIST_REGEX = re.compile(r'www|https|\.pdf|\bnone\b', re.IGNORECASE)


def is_value_containing_blacklisted_terms(text: str) -> bool:
    return bool(BLACKLIST_REGEX.search(text))
