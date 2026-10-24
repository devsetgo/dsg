# -*- coding: utf-8 -*-
"""
A fake PyPI behind httpx.MockTransport, so resolver and app tests exercise the
real index code (PEP 691 parsing, .metadata fetches, JSON fallback, caching)
without the network.

Spec format::

    {
        "pkg": {
            "1.0": {
                "deps": ["other>=1", 'extra-dep; extra == "fancy"'],
                "requires_python": ">=3.8",       # optional
                "wheel": "py3-none-any",          # tag triple, or None for sdist-only
                "sdist": True,                    # also ship an sdist
                "metadata": True,                 # publish PEP 658 .metadata
                "yanked": False,
                "vulns": [{"id": "PYSEC-1", "fixed_in": ["1.1"]}],
            },
        },
    }
"""

from collections import Counter

import httpx
from packaging.utils import canonicalize_name

SIMPLE = "https://pypi.test/simple"
JSON = "https://pypi.test/pypi"
FILES = "https://files.test"


def _wheel_name(name: str, version: str, tag: str) -> str:
    return f"{name.replace('-', '_')}-{version}-{tag}.whl"


def _sdist_name(name: str, version: str) -> str:
    return f"{name.replace('-', '_')}-{version}.tar.gz"


class FakePyPI:
    def __init__(self, spec: dict) -> None:
        self.spec = {canonicalize_name(k): v for k, v in spec.items()}
        self.requests: Counter[str] = Counter()
        self.transport = httpx.MockTransport(self.handle)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self.transport)

    def _files(self, name: str) -> list[dict]:
        files = []
        for version, info in self.spec[name].items():
            common = {
                "requires-python": info.get("requires_python"),
                "yanked": info.get("yanked", False),
            }
            tag = info.get("wheel", "py3-none-any")
            if tag:
                filename = _wheel_name(name, version, tag)
                files.append(
                    {
                        "filename": filename,
                        "url": f"{FILES}/{filename}",
                        "core-metadata": bool(info.get("metadata", True)),
                        **common,
                    }
                )
            if info.get("sdist", tag is None):
                filename = _sdist_name(name, version)
                files.append(
                    {
                        "filename": filename,
                        "url": f"{FILES}/{filename}",
                        "core-metadata": False,
                        **common,
                    }
                )
        return files

    def _find_by_filename(self, filename: str):
        for name, versions in self.spec.items():
            for version, info in versions.items():
                tag = info.get("wheel", "py3-none-any")
                if tag and _wheel_name(name, version, tag) == filename:
                    return name, version, info
        return None

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests[url] += 1
        if url.startswith(f"{SIMPLE}/"):
            name = canonicalize_name(url[len(SIMPLE) + 1 :].strip("/"))
            if name not in self.spec:
                return httpx.Response(404)
            return httpx.Response(
                200,
                json={
                    "name": name,
                    "files": self._files(name),
                    "meta": {"api-version": "1.1"},
                },
            )
        if url.startswith(f"{FILES}/") and url.endswith(".metadata"):
            found = self._find_by_filename(url[len(FILES) + 1 : -len(".metadata")])
            if found is None or not found[2].get("metadata", True):
                return httpx.Response(404)
            name, version, info = found
            lines = ["Metadata-Version: 2.1", f"Name: {name}", f"Version: {version}"]
            if info.get("requires_python"):
                lines.append(f"Requires-Python: {info['requires_python']}")
            lines += [f"Requires-Dist: {dep}" for dep in info.get("deps", [])]
            return httpx.Response(200, content=("\n".join(lines) + "\n").encode())
        if url.startswith(f"{JSON}/"):
            parts = url[len(JSON) + 1 :].strip("/").split("/")
            name, version = canonicalize_name(parts[0]), parts[1]
            info = self.spec.get(name, {}).get(version)
            if info is None:
                return httpx.Response(404)
            # Like PyPI: requires_dist is null when no wheel metadata was extracted
            # (sdist-only releases), unless the test says otherwise via json_deps.
            requires_dist = (
                info.get("deps", [])
                if info.get("wheel", "py3-none-any")
                else info.get("json_deps")
            )
            return httpx.Response(
                200,
                json={
                    "info": {
                        "name": name,
                        "version": version,
                        "requires_dist": requires_dist,
                        "summary": f"{name} summary",
                    },
                    "vulnerabilities": [
                        {
                            "id": v["id"],
                            "aliases": [],
                            "details": "bad",
                            "fixed_in": v.get("fixed_in", []),
                            "link": f"https://osv.dev/{v['id']}",
                            "withdrawn": None,
                        }
                        for v in info.get("vulns", [])
                    ],
                },
            )
        return httpx.Response(404)

    def count(self, fragment: str) -> int:
        return sum(n for url, n in self.requests.items() if fragment in url)
