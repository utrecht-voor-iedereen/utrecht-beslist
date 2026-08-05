"""
Unit tests for the pipeline's staleness diagnosis.
"""

import logging
from datetime import datetime, timedelta, timezone

from scripts.pipeline import diagnose_staleness


def _days_ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).date()


def test_recess_is_not_reported_as_a_fault():
    # Every council quiet for as long as Utrecht: the summer recess, which the
    # bare threshold used to report as a fault every day for six weeks.
    peers = {
        "ori_amsterdam*": _days_ago(34),
        "ori_den_haag*": _days_ago(27),
        "ori_eindhoven*": _days_ago(28),
        "ori_groningen*": _days_ago(30),
    }
    level, message = diagnose_staleness(27, peers)
    assert level == logging.INFO
    assert "recess" in message


def test_utrecht_alone_falling_behind_is_critical():
    peers = {
        "ori_amsterdam*": _days_ago(2),
        "ori_den_haag*": _days_ago(1),
        "ori_eindhoven*": _days_ago(4),
        "ori_groningen*": _days_ago(3),
    }
    level, message = diagnose_staleness(40, peers)
    assert level == logging.CRITICAL
    assert "not" in message


def test_half_the_peers_quiet_counts_as_a_recess():
    # A recess does not start everywhere on the same day, and a council with a
    # meeting in the first week of it should not turn the message into a fault.
    peers = {
        "ori_amsterdam*": _days_ago(30),
        "ori_den_haag*": _days_ago(28),
        "ori_eindhoven*": _days_ago(3),
        "ori_groningen*": _days_ago(5),
    }
    level, _ = diagnose_staleness(25, peers)
    assert level == logging.INFO


def test_unreachable_peers_do_not_claim_a_verdict():
    peers = {"ori_amsterdam*": None, "ori_den_haag*": None}
    level, message = diagnose_staleness(30, peers)
    assert level == logging.ERROR
    assert "cannot tell" in message
