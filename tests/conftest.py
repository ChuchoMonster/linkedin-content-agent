import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# A post that clears every gate with no warnings: a 10-word opener, a number,
# about 110 words, short paragraphs, no closing question.
VALID_BODY = """A small chip startup doubled its valuation in four weeks.

The company raised $700M this week at a $21B valuation. In July the same
investors priced it at $10.3B, so the number moved fast and nobody blinked.

A trading firm led the round, not a venture fund. Trading firms care about
speed and cost per answer, which is exactly what this hardware sells to buyers.

Orders already booked pass $1B and the first systems are shipping to customers
this quarter. That is revenue, not a slide in a pitch deck.

Everyone is still arguing about which model wins the benchmark race. The money
has quietly moved to the boxes that run every model at lower cost."""

VALID_TAGS = "#AIChips #VentureCapital #Semiconductors #DeepTech #Inference"


def make_post(body=VALID_BODY, tags=VALID_TAGS):
    return f"{body}\n\n{tags}\n" if tags is not None else f"{body}\n"


@pytest.fixture
def write_post(tmp_path):
    counter = {"n": 0}

    def _write(text):
        counter["n"] += 1
        path = tmp_path / f"post-{counter['n']}.md"
        path.write_text(text)
        return path

    return _write


@pytest.fixture(autouse=True)
def no_real_credentials(monkeypatch):
    """Make sure no developer credentials leak into a test run."""
    for key in list(os.environ):
        if key.startswith(("BUFFER_", "ASSET_")):
            monkeypatch.delenv(key, raising=False)
