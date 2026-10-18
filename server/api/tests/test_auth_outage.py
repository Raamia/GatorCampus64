"""Auth0 outages must preserve valid cached-key logins without accepting unknown keys."""
import pytest

from sgl_api.auth import AuthError, JWKSCache, Verifier
from .conftest import AUDIENCE, ISSUER


def test_warm_jwks_outage_accepts_cached_signature_but_rejects_unknown_key(jwks, token):
    offline = [False]
    def fetch(_):
        if offline[0]:
            raise OSError('simulated outage')
        return jwks
    cache = JWKSCache('unused', fetch=fetch, ttl=0, min_refetch=0)
    verifier = Verifier(ISSUER, AUDIENCE, cache)
    assert verifier.verify(token()).sub == 'auth0|alice'
    offline[0] = True
    assert verifier.verify(token()).sub == 'auth0|alice'
    with pytest.raises(AuthError) as error:
        verifier.verify(token(kid='new-unavailable-key'))
    assert error.value.status == 401
    with pytest.raises(AuthError) as error:
        verifier.verify(token(exp_in=-60))
    assert error.value.status == 401


def test_cold_jwks_outage_fails_closed(token):
    def unavailable(_):
        raise OSError('simulated outage')
    verifier = Verifier(ISSUER, AUDIENCE, JWKSCache('unused', fetch=unavailable))
    with pytest.raises(AuthError) as error:
        verifier.verify(token())
    assert error.value.status == 503
