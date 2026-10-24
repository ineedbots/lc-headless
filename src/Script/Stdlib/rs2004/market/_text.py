"""The string tests rs2b0t's market writes as regular expressions, for pocketpy, which has no re."""


def is_word_char(c):
    lower = c.lower()
    return ('a' <= lower and lower <= 'z') or ('0' <= c and c <= '9') or c == '_'


def is_digits(text):
    if len(text) == 0:
        return False
    for c in text:
        if not ('0' <= c and c <= '9'):
            return False
    return True


def key(name):
    """A name as the market compares it: lower case, every run of anything but letters and digits one space.

    Why: players type "maple longbow u", so punctuation can't separate them from "Maple longbow (u)"."""
    out = []
    gap = False
    for c in name.lower():
        if ('a' <= c and c <= 'z') or ('0' <= c and c <= '9'):
            if gap and len(out) > 0:
                out.append(' ')
            out.append(c)
            gap = False
        else:
            gap = True
    return ''.join(out)


def squash_spaces(text):
    """Every run of whitespace one space, trimmed."""
    return ' '.join(text.split())


def ends_with_word(name, word):
    """name ends with word, with no word character just before it: rs2b0t's /\\bword$/."""
    if not name.endswith(word):
        return False
    at = len(name) - len(word)
    return at == 0 or not is_word_char(name[at - 1])


def starts_with_word(name, word):
    """name starts with word, with no word character just after it: rs2b0t's /^word\\b/."""
    if not name.startswith(word):
        return False
    return len(name) == len(word) or not is_word_char(name[len(word)])


def replace_word(text, word, by):
    """The first occurrence of word that stands as a whole word, replaced: rs2b0t's .replace(/\\bword\\b/, by)."""
    at = text.find(word)
    while at >= 0:
        end = at + len(word)
        before = at == 0 or not is_word_char(text[at - 1])
        after = end >= len(text) or not is_word_char(text[end])
        if before and after:
            return text[:at] + by + text[end:]
        at = text.find(word, at + 1)
    return text


def format_gp(n):
    """n with thousands commas, as JavaScript's toLocaleString('en-US') gives it."""
    sign = '-' if n < 0 else ''
    digits = str(abs(int(n)))
    groups = []
    while len(digits) > 3:
        groups.insert(0, digits[len(digits) - 3:])
        digits = digits[:len(digits) - 3]
    groups.insert(0, digits)
    return sign + ','.join(groups)
