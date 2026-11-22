"""Regression tests for saving .osi inputs without clobbering user choices.

Before the fix, File -> Save Input ran ``solve_extend_basic_input_dict`` on the
live input dict, which reset every live-load vehicle flag to True (and
re-solved the layout), so the saved file no longer matched the design.
"""
import pytest

from osdagbridge.core.bridge_types.plate_girder.defaults import (
    BASIC_INPUT_DICT,
    solve_extend_basic_input_dict,
    with_missing_defaults,
)
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_FOOTPATH,
    KEY_INCLUDE_MEDIAN,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_SKEW_ANGLE,
    KEY_SPAN,
    KEY_TS_GIRDER_SPACING,
)


@pytest.fixture
def designed_inputs():
    d = dict(BASIC_INPUT_DICT)
    d.update({
        KEY_SPAN: "35", KEY_CARRIAGEWAY_WIDTH: "7.5", KEY_FOOTPATH: "Both Sides",
        KEY_INCLUDE_MEDIAN: "No", KEY_SKEW_ANGLE: "0",
    })
    solve_extend_basic_input_dict(d)
    # user deselects three vehicles and edits a layout value afterwards
    d[KEY_LL_IRC_AA_WHEELED] = False
    d[KEY_LL_IRC_AA_TRACKED] = False
    d[KEY_LL_IRC_70R_BOGIE] = False
    d[KEY_TS_GIRDER_SPACING] = 2.9875
    return d


def test_user_values_are_preserved(designed_inputs):
    out = with_missing_defaults(designed_inputs)
    assert out[KEY_LL_IRC_AA_WHEELED] is False
    assert out[KEY_LL_IRC_AA_TRACKED] is False
    assert out[KEY_LL_IRC_70R_BOGIE] is False
    assert out[KEY_LL_IRC_CLASS_A] is True
    assert out[KEY_TS_GIRDER_SPACING] == 2.9875


def test_missing_keys_get_defaults(designed_inputs):
    del designed_inputs[KEY_LL_IRC_CLASS_FATIGUE]
    out = with_missing_defaults(designed_inputs)
    assert out[KEY_LL_IRC_CLASS_FATIGUE] is True


def test_input_dict_is_not_mutated(designed_inputs):
    snapshot = dict(designed_inputs)
    with_missing_defaults(designed_inputs)
    assert designed_inputs == snapshot
