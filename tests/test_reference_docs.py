"""The CLI and HTTP API reference in docs/REFERENCE.md must match the code.

A boundary documented with the wrong fields is the exact failure mode the lab
exists to avoid: a promise about an interface that is not the interface. This
module keeps the prose honest, mirroring the CI drift check on the source
register.
"""

import re
import unittest
from pathlib import Path

from jev_lab import server

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = (ROOT / "docs" / "REFERENCE.md").read_text()

POST_ROUTES = frozenset(server.FIELDS)
GET_ROUTES = frozenset({"/api/config", "/api/studio", "/api/cases", "/api/signals"})
CLI_COMMANDS = frozenset({"serve", "check", "smoke", "eval", "bench", "compare"})


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _fields_cell(cell: str) -> set[str]:
    return set(re.findall(r"`([a-z_]+)`", cell))


class ReferenceDocsTests(unittest.TestCase):
    def test_every_post_route_is_documented_with_exact_fields(self):
        documented = {}
        for line in REFERENCE.splitlines():
            if not line.startswith("| `POST "):
                continue
            cells = _cells(line)
            route = re.match(r"`(POST /api/[a-z-]+)`", cells[0]).group(1)
            documented[route.removeprefix("POST ")] = _fields_cell(cells[1])
        self.assertEqual(documented, dict(server.FIELDS))

    def test_every_get_route_is_documented(self):
        documented = set()
        for line in REFERENCE.splitlines():
            if not line.startswith("| `GET "):
                continue
            route = re.match(r"`(GET /api/[a-z-]+)`", _cells(line)[0]).group(1)
            documented.add(route.removeprefix("GET "))
        self.assertEqual(documented, GET_ROUTES)

    def test_every_cli_command_is_documented(self):
        documented = set()
        for line in REFERENCE.splitlines():
            match = re.match(r"\| `([a-z]+)`", line)
            if not match:
                continue
            candidate = match.group(1)
            if candidate in CLI_COMMANDS:
                documented.add(candidate)
        self.assertEqual(documented, CLI_COMMANDS)
