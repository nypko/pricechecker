"""Scraped text (store terms, promotion lines, brand spec pages) going into a GitHub issue body: always inside a code
fence longer than any run of backticks in it, so the page can't close the fence and inject markdown (links, images,
fake instructions), and with every @ followed by a zero-width space, so it can't @mention (notify) anyone."""
import re

ZWSP = "\u200b"


def defuse(text: str) -> str:
    """'@someone' -> '@\\u200bsomeone': still readable, never a mention."""
    return text.replace("@", "@" + ZWSP)


def fence(lines: list[str] | str, lang: str = "") -> list[str]:
    """The lines as a fenced block (a list of lines, fence lines included), the fence one backtick longer than the
    longest backtick run inside (at least three)."""
    body = [defuse(ln) for ln in (lines.splitlines() if isinstance(lines, str) else lines)]
    longest = max((len(m) for ln in body for m in re.findall(r"`+", ln)), default=0)
    bar = "`" * max(3, longest + 1)
    return [bar + lang, *body, bar]
