from pathlib import Path


BOOTSTRAP = Path("firmware/reven-recovery/REVEN_RECOVERY_BOOTSTRAP/REVEN_RECOVERY_BOOTSTRAP.ino")


def test_reven_recovery_supports_saved_wifi_and_fallback_ap():
    src = BOOTSTRAP.read_text()
    required = [
        "#include <Preferences.h>",
        'prefs.getString("ssid"',
        'prefs.getString("pass"',
        'prefs.putString("ssid"',
        'prefs.putString("pass"',
        'server.on("/save"',
        "WiFi.begin(",
        "WL_CONNECTED",
        "WiFi.softAP(",
        'name="ssid"',
        'name="pass"',
        "SETUP AP READY",
        "WIFI CONNECTED",
    ]
    missing = [token for token in required if token not in src]
    assert not missing, f"missing provisioning/fallback features: {missing}"


def test_reven_recovery_does_not_hardcode_home_credentials():
    src = BOOTSTRAP.read_text()
    assert "HOME_WIFI" not in src
    assert "HOME_PASS" not in src
