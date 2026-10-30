"""Separate requested noun phrases from explicit navigation exclusions.

This is scheduling input, not product qualification. Hyphenated descriptors are
words; sentence/list boundaries and exclusion predicates delimit their scope.
"""
import re

_PREFIX = re.compile(r"(?<![\w-])(?:but\s+not|no|not|without|excluding|exclude|except(?:\s+for)?|"
                     r"(?:\w+n't|do\s+not)\s+(?:want|need|include))(?![\w-])\s+", re.I)
_POSTFIX = re.compile(r"\b(?:not\s+(?:included|required|wanted)|excluded|optional|out\s+of\s+scope)\b", re.I)
_NOUN_LIST = re.compile(r"[\w-]+(?:\s+(?:and|or)\s+[\w-]+)*\s*$", re.I)


def split_brief(product):
    positive, excluded = [], []
    def parenthetical(match):
        value = match[1]
        if _PREFIX.search(value) or _POSTFIX.search(value):
            excluded.append(value)
            return " "
        return match[0]
    product = re.sub(r"\(([^()]*)\)", parenthetical, product or "")
    for part in re.split(r"[,;\n]|(?<=[.!?])\s+", product):
        if match := _POSTFIX.search(part):
            subject = _NOUN_LIST.search(part[:match.start()])
            start = subject.start() if subject else 0
            positive.append(part[:start])
            excluded.append(part[start:])
        elif match := _PREFIX.search(part):
            positive.append(part[:match.start()])
            excluded.append(part[match.start():])
        else:
            positive.append(part)
    return " ".join(p.strip() for p in positive if p.strip()), excluded


def positive_brief(product):
    return split_brief(product)[0]
