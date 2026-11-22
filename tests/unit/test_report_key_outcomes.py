"""Executive Summary 'Key Design Outcomes' come from the design results
(they used to be four static 'design pass' lines)."""
from osdagbridge.core.reports.executive_summary import executive_summary


def _outcomes(output_dict):
    tex = executive_summary({}, output_dict, {})
    block = tex.split(r"\label{sec:key-outcomes}")[1].split(r"\section*")[0]
    return block


def _girder(dcr, status):
    return {"design_results": {"per_girder": {"G1": {"checks": [
        {"name": "Fatigue Normal Stress", "dcr": dcr, "status": status}]}}}}


def test_failing_girder_is_reported_as_fail():
    out = _outcomes({**_girder(1.86, "FAIL"), "deck_design_results": {"ur_flexure": 0.5}})
    assert "Girder design:" in out and "FAIL (max. UR 1.86)" in out
    assert "Deck design:" in out and "PASS (max. UR 0.50)" in out
    assert "design pass" not in out


def test_passing_girder_is_reported_as_pass():
    out = _outcomes(_girder(0.75, "PASS"))
    assert "PASS (max. UR 0.75)" in out


def test_missing_results_are_not_reported_as_pass():
    out = _outcomes({})
    assert out.count("no design results") == 3      # girder, cross bracing, deck
    assert "no member design performed" in out      # end diaphragm
    assert "PASS" not in out
