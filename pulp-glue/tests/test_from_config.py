import pytest
from pydantic import ValidationError

from pulp_glue.common.context import PulpContext


class TestFromConfig:
    def test_empty_config_results_in_defaults(self) -> None:
        pulp_ctx = PulpContext.from_config({})
        assert pulp_ctx._api_root == "/pulp/"

    def test_invalid_config_fails_validation(self) -> None:
        with pytest.raises(ValidationError):
            PulpContext.from_config({"base_url": 1})

    def test_extra_keys_are_ignored(self) -> None:
        PulpContext.from_config({"idontknow": 6})

    def test_fake_mode_can_be_specified(self) -> None:
        pulp_ctx = PulpContext.from_config({"fake_mode": True})
        assert pulp_ctx.fake_mode is True
