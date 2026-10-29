"""Versioned JS modules. /static/js/* is cached for a year, so every relative import between modules carries ?v=<hash>
of the imported file: a change in b.js changes the hash in a.js, which changes a.js's own hash (and its ?v= in pages)."""
import hashlib
import re
from pathlib import Path

_SPEC = re.compile(r"""(\b(?:from|import)\s*)(["'])(\./[^"'?]+\.js)\2""")


def _short(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:10]


def versioned_modules(src: Path) -> dict[str, tuple[str, str]]:
    """{file name: (text with ./x.js imports rewritten to ./x.js?v=hash, hash of that text)} for src/*.js."""
    raw = {p.name: p.read_text() for p in sorted(src.glob("*.js"))}
    done: dict[str, tuple[str, str]] = {}

    def build(name: str, stack: tuple[str, ...]) -> tuple[str, str]:
        if name in done:
            return done[name]
        if name in stack:
            raise ValueError(f"circular import: {' -> '.join((*stack, name))}")

        def sub(m: re.Match) -> str:
            dep = m.group(3)[2:]
            if dep not in raw:
                raise ValueError(f"{name} imports missing {dep}")
            return f"{m.group(1)}{m.group(2)}./{dep}?v={build(dep, (*stack, name))[1]}{m.group(2)}"

        text = _SPEC.sub(sub, raw[name])
        done[name] = (text, _short(text))
        return done[name]

    for n in raw:
        build(n, ())
    return done
