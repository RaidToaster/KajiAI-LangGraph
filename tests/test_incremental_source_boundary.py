from kaji_langgraph.incremental.providers import Providers, benchmark_source


def test_benchmark_mirrors_and_repository_answer_files_are_rejected():
    assert benchmark_source("https://github.com/organization/AVeriTeC/blob/main/data/dev.json")
    assert benchmark_source("https://huggingface.co/datasets/example/factchecks")
    assert benchmark_source("https://raw.githubusercontent.com/example/research/main/dev.json")
    assert benchmark_source("https://redirect.example/?url=https%3A%2F%2Fexample.org%2FAVeriTeC%2Fdev.json")
    assert benchmark_source("https://example.org/data", "AVeriTeC annotated answers")


def test_organic_factchecks_and_primary_records_remain_eligible():
    assert not benchmark_source("https://www.politifact.com/factchecks/2020/01/01/example/")
    assert not benchmark_source("https://www.factcheck.org/2020/01/example/")
    assert not benchmark_source("https://www.senate.gov/legislative/votes.htm")
    assert not benchmark_source("https://github.com/official-agency/historical-records/blob/main/report.pdf")


def test_disallowed_fetch_is_rejected_before_provider_dispatch():
    class NoSend:
        def reserve(self, *args):
            raise AssertionError("Must not reserve or dispatch a forbidden fetch")
    provider = Providers(NoSend(), "http://localhost:11434")
    text, status, error = provider.fetch("https://github.com/example/AVeriTeC/dev.json")
    assert not text and status is None
    assert "before Fetch dispatch" in error
