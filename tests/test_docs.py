"""The documentation is executable: doctests, README and GUIDE examples and transcripts run."""

from __future__ import annotations

import doctest
import importlib
import inspect
import pkgutil
import re
import shlex
from pathlib import Path

import pytest
from _cli_command import run_cli

import lvtime

_ROOT = Path(__file__).resolve().parent.parent
_MODULES = ["lvtime"] + [f"lvtime.{m.name}" for m in pkgutil.iter_modules(lvtime.__path__)]
_PYCON = re.compile(r"```pycon\n(.*?)```", re.DOTALL)
_SHELL = re.compile(r"```\n(\$ lvtime.*?)```", re.DOTALL)
_DOCS = ["README.md", "GUIDE.md"]


@pytest.mark.parametrize("name", _MODULES)
def test_module_doctests_pass(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name))
    assert result.failed == 0


@pytest.mark.parametrize(
    "name",
    [
        n
        for n in lvtime.__all__
        if inspect.isfunction(getattr(lvtime, n)) or inspect.isclass(getattr(lvtime, n))
    ],
)
def test_every_public_callable_has_a_docstring_with_an_example(name: str) -> None:
    doc = getattr(lvtime, name).__doc__ or ""
    assert ">>>" in doc, name


@pytest.mark.parametrize(
    "name", [n for n, _ in inspect.getmembers(lvtime.LVTimestamp) if not n.startswith("_")]
)
def test_every_public_method_has_an_example(name: str) -> None:
    member = getattr(lvtime.LVTimestamp, name)
    if callable(member):
        assert ">>>" in (member.__doc__ or ""), name


def test_the_doctests_cover_every_public_name() -> None:
    finder = doctest.DocTestFinder()
    examples = "".join(
        example.source
        for module in _MODULES
        for test in finder.find(importlib.import_module(module))
        for example in test.examples
    )
    for name in lvtime.__all__:
        assert re.search(rf"\b{name}\b", examples), name


@pytest.mark.parametrize("document", _DOCS)
def test_document_examples_run_and_print_what_they_show(document: str) -> None:
    blocks = _PYCON.findall((_ROOT / document).read_text(encoding="utf-8"))
    assert blocks, document
    parser = doctest.DocTestParser()
    runner = doctest.DocTestRunner()
    for number, block in enumerate(blocks):
        test = parser.get_doctest(block, {}, f"{document}[{number}]", document, 0)
        runner.run(test)
    assert runner.summarize(verbose=False).failed == 0


def _transcripts(document: str) -> list[tuple[list[str], str]]:
    runs: list[tuple[list[str], str]] = []
    for block in _SHELL.findall((_ROOT / document).read_text(encoding="utf-8")):
        for chunk in block.split("$ lvtime")[1:]:
            command, _, output = chunk.partition("\n")
            runs.append((shlex.split(command), output))
    return runs


@pytest.mark.parametrize("document", _DOCS)
def test_document_transcripts_match_the_real_command(document: str) -> None:
    runs = _transcripts(document)
    assert runs, document
    for args, output in runs:
        result = run_cli(*args)
        assert result.returncode == 0, (args, result.stderr)
        assert result.stdout == output, args


def test_guide_covers_every_public_name() -> None:
    text = (_ROOT / "GUIDE.md").read_text(encoding="utf-8")
    for name in lvtime.__all__:
        assert re.search(rf"\b{name}\b", text), name


def test_examples_import_only_public_names() -> None:
    for document in _DOCS:
        text = (_ROOT / document).read_text(encoding="utf-8")
        for module, names in re.findall(r"from (lvtime\S*) import ([^\n]+)", text):
            assert module == "lvtime", (document, module)
            for name in names.split(","):
                assert name.strip() in lvtime.__all__, (document, name)


def test_readme_links_are_absolute() -> None:
    text = (_ROOT / "README.md").read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        assert target.startswith("https://"), target
