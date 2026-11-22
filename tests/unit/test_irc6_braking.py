"""Regression tests for IRC6_2017.cl_211_2_braking_force.

Before the fix the function raised UnboundLocalError for every lane count
(braking_force_2 was read before assignment), so the report always showed
"N/A". The formula itself is unchanged: 20 % of the Class A train for the
first two lanes plus 5 % of the Class 70R (wheeled) train for lanes > 2.
"""
import pytest

from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.codes.keyfile import t

CLASS_A_T = sum(IRC6_2017.cl_204_1_ClassA_vehicle()["wheel_loads"]) / t
CLASS_70R_T = sum(IRC6_2017.cl_204_1_Class70R_vehicle_wheel()["wheel_loads"]) / t


def test_vehicle_definitions_are_the_irc_trains():
    # IRC 6:2017 Cl.204.1 train weights
    assert CLASS_A_T == pytest.approx(55.4)
    assert CLASS_70R_T == pytest.approx(100.0)


@pytest.mark.parametrize("lanes", [1, 2])
def test_one_and_two_lanes_do_not_crash(lanes):
    assert IRC6_2017.cl_211_2_braking_force(lanes) == pytest.approx(0.20 * CLASS_A_T, abs=1e-3)


@pytest.mark.parametrize("lanes", [3, 4, 6])
def test_more_than_two_lanes_adds_the_existing_70r_term(lanes):
    expected = 0.20 * CLASS_A_T + 0.05 * CLASS_70R_T
    assert IRC6_2017.cl_211_2_braking_force(lanes) == pytest.approx(expected, abs=1e-3)


def test_result_is_in_tonnes_as_documented():
    # 20 % of 55.4 t: a value in N would be ~1e5, in kN ~108.7
    assert IRC6_2017.cl_211_2_braking_force(2) == pytest.approx(11.08, abs=1e-3)
