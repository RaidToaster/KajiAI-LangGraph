from __future__ import annotations

from copy import deepcopy

import pytest

from kaji_langgraph.config import load_config
from kaji_langgraph.llm import DeterministicBackend
from kaji_langgraph.retrieval import StaticRetriever


@pytest.fixture
def config():
    value = deepcopy(load_config())
    value["policy"].update(
        full_page_retrieval=False,
        max_execution_time_seconds=30,
        max_search_calls=4,
        search_calls_per_round=1,
        retry_delay_seconds=0,
    )
    return value


@pytest.fixture
def backend():
    return DeterministicBackend()


@pytest.fixture
def two_source_retriever():
    return StaticRetriever(
        [
            {
                "title": "Primary record",
                "href": "https://one.example/record",
                "body": "The official record directly confirms the test claim and event date.",
            },
            {
                "title": "Independent archive",
                "href": "https://two.example/archive",
                "body": "An independent archive separately verifies the test claim from original records.",
            },
        ]
    )
