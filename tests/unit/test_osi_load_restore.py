"""Exercise the desktop Load Input path with a saved location and vehicle flags."""

import pytest
import yaml

from osdagbridge.core.bridge_types.plate_girder.defaults import BASIC_INPUT_DICT
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_FOOTPATH,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_PROJECT_LOCATION,
    KEY_SKEW_ANGLE,
    KEY_SPAN,
    KEY_TS_GIRDER_SPACING,
    KEY_TS_OVERALL_WIDTH,
)


@pytest.fixture(scope="module")
def qt_app():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("QT_QPA_PLATFORM", "offscreen")
        app = widgets.QApplication.instance() or widgets.QApplication([])
        yield app, widgets


@pytest.fixture
def desktop(qt_app, monkeypatch):
    app, widgets = qt_app
    from shiboken6 import delete

    pytest.importorskip("OCC")
    from osdagbridge.desktop import __main__  # Registers Qt resources.
    from osdagbridge.desktop.ui import template_page
    from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge

    # Loading an OSI refreshes 2D CAD. The native 3D renderer is unrelated
    # and can fail during teardown on Qt's offscreen platform.
    monkeypatch.setattr(template_page, "CAD3DWindow", widgets.QWidget)
    window = template_page.CustomWindow("OSI restore test", PlateGirderBridge)
    yield window, widgets, template_page
    delete(window._additional_inputs_dialog)
    delete(window)
    app.processEvents()


def test_load_osi_preserves_saved_location_vehicles_and_layout(desktop, tmp_path, monkeypatch):
    window, widgets, template_page = desktop
    location = {
        "method": "location_name",
        "data": {"state": "Tamil Nadu", "district": "Chennai (Minambakkam) (A)"},
        "display_text": "Chennai (Minambakkam) (A), Tamil Nadu",
        "show_display": True,
        "weather_data": {
            "latitude": 12.9855, "longitude": 80.1689, "zone": "III",
            "z_value": 0.16, "wind_speed": 50, "max_temp": 49.1, "min_temp": 15.7,
        },
    }
    selected = {
        KEY_LL_IRC_CLASS_A, KEY_LL_IRC_70R_WHEELED, KEY_LL_IRC_70R_TRACKED,
        KEY_LL_IRC_CLASS_SV, KEY_LL_IRC_CLASS_FATIGUE,
    }
    unselected = {KEY_LL_IRC_AA_WHEELED: 0, KEY_LL_IRC_AA_TRACKED: False, KEY_LL_IRC_70R_BOGIE: 0}
    data = {
        **BASIC_INPUT_DICT, **dict.fromkeys(selected, True), **unselected,
        KEY_SPAN: "35", KEY_CARRIAGEWAY_WIDTH: "7.5", KEY_FOOTPATH: "Both Sides",
        KEY_SKEW_ANGLE: "0", KEY_PROJECT_LOCATION: location,
        KEY_TS_GIRDER_SPACING: 2.9875, KEY_TS_OVERALL_WIDTH: 11.95,
    }
    messages = []

    class MessageBox:
        def __init__(self, **kwargs):
            messages.append(kwargs["title"])

        def exec(self):
            pass

    osi = tmp_path / "saved.osi"
    osi.write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(template_page.QFileDialog, "getOpenFileName", lambda *_: (str(osi), ""))
    monkeypatch.setattr(template_page, "CustomMessageBox", MessageBox)
    window.loadOSI_inputs()

    assert messages == ["Success"]
    dock = window.input_dock
    assert not dock.is_require_field_changed
    assert dock._w(f"{KEY_PROJECT_LOCATION}_info_label").text() == location["display_text"]
    assert not dock._w(f"{KEY_PROJECT_LOCATION}_info_row").isHidden()
    assert window.input_dict[KEY_PROJECT_LOCATION] == location
    assert window.input_dict[KEY_TS_GIRDER_SPACING] == 2.9875
    assert window.input_dict[KEY_TS_OVERALL_WIDTH] == 11.95
    dialog = window._get_additional_inputs()
    for key in selected | unselected.keys():
        assert dialog.findChild(widgets.QCheckBox, key).isChecked() == (key in selected)
        assert bool(window.input_dict[key]) == (key in selected)

    # Loading a file with no location clears the previous file's location row.
    data[KEY_PROJECT_LOCATION] = None
    osi.write_text(yaml.safe_dump(data), encoding="utf-8")
    window.loadOSI_inputs()
    assert messages == ["Success", "Success"]
    assert dock._w(f"{KEY_PROJECT_LOCATION}_info_row").isHidden()


def test_location_dialog_prefers_saved_project_over_session(desktop, monkeypatch):
    from shiboken6 import delete
    from osdagbridge.desktop.ui.dialogs import project_location

    monkeypatch.setattr(project_location, "LAST_LOCATION_METHOD", "location_name")
    previous = {"state": "Maharashtra", "district": "Mumbai"}
    monkeypatch.setattr(project_location, "LAST_LOCATION_DATA", previous)
    location = {"method": "location_name",
                "data": {"state": "Tamil Nadu", "district": "Chennai (Minambakkam) (A)"}}
    dialog = project_location.ProjectLocationDialog(location=location)
    assert dialog.get_selected_location()["data"] == location["data"]
    dialog.reject()
    assert project_location.LAST_LOCATION_DATA == previous
    delete(dialog)
