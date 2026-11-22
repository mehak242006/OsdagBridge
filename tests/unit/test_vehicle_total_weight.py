"""BridgeGrillageModel._vehicle_total_weight_kN — totals from existing IRC6_2017
vehicle definitions, checked against the IRC 6:2017 train weights."""
import pytest

from osdagbridge.core.bridge_types.plate_girder.analyser import BridgeGrillageModel
from osdagbridge.core.utils.codes.keyfile import g

total = BridgeGrillageModel._vehicle_total_weight_kN


@pytest.mark.parametrize("vehicle, tonnes", [
    ("ClassA", 55.4),            # IRC 6 Cl. 204.1 (unchanged behaviour)
    ("Class70R", 100.0),         # IRC 6 Cl. 204.1 wheeled (unchanged behaviour)
    ("Fatigue", 40.0),           # IRC 6 Cl. 204.6 fatigue truck
    ("ClassSV", 385.0),          # IRC 6 Cl. 204.5 special vehicle
])
def test_totals_match_irc_train_weights(vehicle, tonnes):
    assert total(vehicle) == pytest.approx(tonnes * g, rel=1e-9)


def test_tracked_70r_total_from_udl_definition():
    # 7.66 t/m (rounded in the definition) x 4.57 m x 2 tracks = 70.01 t
    assert total("Class70R_Tracked") == pytest.approx(7.66 * 4.57 * 2 * g, rel=1e-9)
    assert total("Class70R_Tracked") == pytest.approx(70.0 * g, rel=1e-3)


def test_special_vehicle_uses_declared_total_not_mis_scaled_wheel_loads():
    # its wheel_loads sum to only ~3.78 (kN numbers in an N-based system)
    assert total("ClassSV") > 3000.0


@pytest.mark.parametrize("vehicle", ["ClassAA_Wheeled", "ClassAA_Tracked", "Class70R_Bogie", "Custom", ""])
def test_vehicles_without_a_definition_return_zero(vehicle):
    assert total(vehicle) == 0.0
