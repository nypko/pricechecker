"""Local preview of build/ that resolves URLs the way Cloudflare Pages does: /phones/x -> phones/x.html.
Usage: python -m pricechecker.serve [port]   (default 8765)"""
import functools
import http.server
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent / "build"


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        local = Path(super().translate_path(path))
        if not local.exists() and local.with_name(local.name + ".html").is_file():
            return str(local.with_name(local.name + ".html"))
        return str(local)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = functools.partial(Handler, directory=str(BUILD))   # a path string, so rebuilds of build/ are picked up
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as srv:
        print(f"Serving {BUILD} at http://127.0.0.1:{port}/")
        srv.serve_forever()


if __name__ == "__main__":
    main()
