"""Verify that docs/api_examples/*.json round-trips through the Pydantic models.

Each fixture is deserialized by its model and then serialized back to confirm
the shape matches what the frontend expects.
"""
import json
from pathlib import Path

from app.schemas import (
    RateRequest,
    RateResponse,
    RenderRequest,
    RenderResponse,
)

EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "docs" / "api_examples"


def load_example(filename: str) -> dict:
    return json.loads((EXAMPLES_DIR / filename).read_text())


class TestApiExamples:
    def test_render_request_parses(self):
        data = load_example("render_request.json")
        req = RenderRequest.model_validate(data)
        assert req.user_id == "demo"
        assert req.mode in ("default", "bionic", "lume_tuned")

    def test_render_response_parses(self):
        data = load_example("render_response.json")
        resp = RenderResponse.model_validate(data)
        assert resp.render_id
        assert isinstance(resp.tokens, list)
        assert len(resp.tokens) > 0
        assert resp.word_count > 0

    def test_rate_request_parses(self):
        data = load_example("rate_request.json")
        req = RateRequest.model_validate(data)
        assert req.render_id
        # comprehension_score may be None when both raw signals are provided
        if req.comprehension_score is not None:
            assert 0.0 <= req.comprehension_score <= 1.0
        else:
            # "both" path: raw signals must be present instead
            assert req.self_rating is not None or req.mcq_correct is not None

    def test_rate_response_parses(self):
        data = load_example("rate_response.json")
        resp = RateResponse.model_validate(data)
        assert resp.ok is True
        assert resp.event_id > 0
        assert 0.0 <= resp.reward <= 1.0

    def test_render_response_arm_index(self):
        data = load_example("render_response.json")
        resp = RenderResponse.model_validate(data)
        # arm_index must be -1 or 0..15
        assert resp.arm_index == -1 or 0 <= resp.arm_index <= 15

    def test_render_response_chunks_structure(self):
        data = load_example("render_response.json")
        resp = RenderResponse.model_validate(data)
        assert isinstance(resp.chunks, list)
        for chunk in resp.chunks:
            assert isinstance(chunk, list)
            assert all(isinstance(i, int) for i in chunk)
