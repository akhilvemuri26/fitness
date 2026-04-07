from app.services.connectors.whoop import WhoopClient, verify_whoop_signature


def test_whoop_auth_url_contains_required_parameters() -> None:
    url = WhoopClient.build_authorization_url(
        client_id="abc123",
        redirect_uri="http://localhost/callback",
        state="teststate",
        scopes=["offline", "read:profile", "read:workout"],
    )

    assert "client_id=abc123" in url
    assert "response_type=code" in url
    assert "state=teststate" in url
    assert "offline" in url


def test_whoop_signature_validation() -> None:
    body = b'{"type":"workout.updated","id":"abc"}'
    secret = "supersecret"
    import hashlib
    import hmac

    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    assert verify_whoop_signature(body, signature, secret) is True
    assert verify_whoop_signature(body, "sha256=" + signature, secret) is True
    assert verify_whoop_signature(body, "bad", secret) is False
