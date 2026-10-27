"""A quest journal as one line to search: rs2b0t's api/ai/quests/journalText.ts (MIT, see thirdparty/rs2b0t)."""

__all__ = ['normalize_journal']

_TAG_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789'


def _strip_tags(text):
    # Why: a colour tag leaves a space where it stood, as rs2b0t's does, so "potion@dbl@." reads "potion ." and a needle
    # mustn't span a tag next to a mark.
    out = ''
    i = 0
    while i < len(text):
        if text[i] == '@' and i + 4 < len(text) and text[i + 4] == '@':
            tag = text[i + 1:i + 4].lower()
            if tag[0] in _TAG_CHARS and tag[1] in _TAG_CHARS and tag[2] in _TAG_CHARS:
                out += ' '
                i += 5
                continue
        out += text[i]
        i += 1
    return out


def normalize_journal(lines):
    """The journal's lines (or one string) joined, without colour tags or pipes, spaces collapsed, lower case."""
    text = lines if isinstance(lines, str) else ' '.join(lines)
    # pocketpy's character indexing fails on the loading ellipsis in journal placeholders.
    text = text.replace('…', '...')
    return ' '.join(_strip_tags(text).replace('|', ' ').split()).lower()
