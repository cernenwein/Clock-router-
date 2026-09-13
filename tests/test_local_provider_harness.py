import pytest

from scripts.local_provider_harness import select_model, validate_local_url


def test_loopback_url_is_allowed() -> None:
    assert validate_local_url(
        "http://127.0.0.1:1234/v1/", allow_private_network=False
    ) == "http://127.0.0.1:1234/v1"


def test_private_network_requires_explicit_opt_in() -> None:
    with pytest.raises(ValueError, match="allow-private-network"):
        validate_local_url("http://192.168.0.90:1234/v1", allow_private_network=False)
    assert (
        validate_local_url("http://192.168.0.90:1234/v1", allow_private_network=True)
        == "http://192.168.0.90:1234/v1"
    )


def test_public_address_is_rejected_even_with_opt_in() -> None:
    with pytest.raises(ValueError, match="public"):
        validate_local_url("https://8.8.8.8/v1", allow_private_network=True)


def test_select_model_uses_requested_exact_id() -> None:
    payload = {"data": [{"id": "model-a"}, {"id": "model-b"}]}
    assert select_model(payload, "model-b") == "model-b"


def test_select_model_defaults_to_first_reported_model() -> None:
    assert select_model({"data": [{"id": "model-a"}]}, None) == "model-a"


def test_select_model_rejects_missing_model() -> None:
    with pytest.raises(ValueError, match="unavailable"):
        select_model({"data": [{"id": "model-a"}]}, "missing")
