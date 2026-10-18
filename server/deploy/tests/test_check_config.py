import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_config import login_checks

EXPECTED = {'domain': 'tenant.example', 'audience': 'https://api.example'}
CONFIG = {'AUTH0_CLIENT_ID': 'native-client-id', 'AUTH0_DOMAIN': 'tenant.example',
          'AUTH0_AUDIENCE': 'https://api.example'}


def test_correct_effective_configuration_passes():
    assert all(login_checks(EXPECTED, CONFIG, CONFIG).values())


def test_combined_assignments_are_detected_without_exposing_values():
    running = {**CONFIG, 'AUTH0_CLIENT_ID': CONFIG['AUTH0_CLIENT_ID'] + ' AUTH0_AUDIENCE=https://old.example'}
    checks = login_checks(EXPECTED, CONFIG, running)
    assert not checks['bridge_running_client_matches_file']
    assert not checks['bridge_running_client_is_single_id']
    assert set(checks.values()) <= {True, False}
    assert 'old.example' not in str(checks)


def test_inline_comments_and_unloaded_changes_fail():
    for client in ('native-client-id # native app', 'different-client-id', ''):
        assert not login_checks(EXPECTED, CONFIG, {**CONFIG, 'AUTH0_CLIENT_ID': client})['bridge_running_client_matches_file']
    assert not all(login_checks(EXPECTED, CONFIG, {}).values())


def test_running_domain_and_audience_are_checked_separately():
    checks = login_checks(EXPECTED, CONFIG, {**CONFIG, 'AUTH0_DOMAIN': 'wrong.example', 'AUTH0_AUDIENCE': 'wrong-api'})
    assert not checks['bridge_running_domain_matches_browser']
    assert not checks['bridge_running_audience_matches_browser']
