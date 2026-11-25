#!/usr/bin/env python3
"""Preview the portfolio on this computer."""

import argparse
import errno
import mimetypes
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from render import render


ROOT = Path(__file__).resolve().parent
STATIC = {name: ROOT / name for name in ("assets", "media")}
TYPES = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".mp4": "video/mp4",
}
BUFFER_SIZE = 256 * 1024


def byte_range(value, size):
    """Return the inclusive interval for a single byte range."""
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", value.strip())
    if not match or not any(match.groups()) or size == 0:
        raise ValueError("Invalid range")
    first, last = match.groups()
    if not first:
        length = int(last)
        if length == 0:
            raise ValueError("Empty range")
        return max(0, size - length), size - 1
    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start > end:
        raise ValueError("Unsatisfiable range")
    return start, end


def video_parts(path, directory):
    """Locate a film stored in numbered parts, in playback order."""
    parts = sorted(path.parent.glob(path.name + ".part[0-9][0-9][0-9]"))
    for number, part in enumerate(parts, start=1):
        if (part.name != f"{path.name}.part{number:03d}"
                or not part.resolve().is_relative_to(directory) or not part.is_file()):
            return []
    return parts


class PortfolioRequest(BaseHTTPRequestHandler):
    server_version = "Studio"

    def do_HEAD(self):
        self.handle_request(include_body=False)

    def do_GET(self):
        self.handle_request(include_body=True)

    def handle_request(self, include_body):
        try:
            path = unquote(urlsplit(self.path).path, errors="strict")
            if not path.startswith("/") or "\x00" in path or "\\" in path:
                self.send_error(400)
                return
            directory, _, filename = path[1:].partition("/")
            if directory in STATIC:
                self.serve_file(STATIC[directory], filename, include_body)
                return

            status, html = render(path)
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            if include_body:
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (UnicodeError, ValueError):
            self.send_error(400)

    def serve_file(self, directory, filename, include_body):
        path = (directory / filename).resolve()
        if not path.is_relative_to(directory):
            self.send_error(404)
            return

        if path.is_file():
            parts = [path]
        elif directory == STATIC["media"] and path.suffix.lower() == ".mp4":
            parts = video_parts(path, directory)
        else:
            parts = []
        if not parts:
            self.send_error(404)
            return

        sizes = [part.stat().st_size for part in parts]
        size = sum(sizes)
        start, end = 0, size - 1
        status = 200
        requested = self.headers.get("Range")
        if requested:
            try:
                start, end = byte_range(requested, size)
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            status = 206

        self.send_response(status)
        content_type = TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0]
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if not include_body:
            return

        offset = 0
        for part, length in zip(parts, sizes):
            first = max(start - offset, 0)
            stop = min(end + 1 - offset, length)
            if first < stop:
                with part.open("rb") as stream:
                    stream.seek(first)
                    remaining = stop - first
                    while remaining:
                        chunk = stream.read(min(remaining, BUFFER_SIZE))
                        if not chunk:
                            return
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            offset += length
            if offset > end:
                break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4187)
    parser.add_argument("--open", action="store_true", help="open the preview in your browser")
    options = parser.parse_args()
    if not 0 <= options.port <= 65535:
        parser.error("port must be between 0 and 65535")

    try:
        server = ThreadingHTTPServer(("127.0.0.1", options.port), PortfolioRequest)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        server = ThreadingHTTPServer(("127.0.0.1", 0), PortfolioRequest)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Preview  {url}\nPress Control-C to stop.", flush=True)
    with server:
        if options.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
