#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>

static const char *SETUP_WIFI_NAME = "REVEN";
static const char *SETUP_WIFI_PASS = "reven1234";
static const uint32_t WIFI_CONNECT_TIMEOUT_MS = 12000;

static WebServer server(80);
static Preferences prefs;
static bool stationConnected = false;
static bool setupApActive = false;

static const char PAGE[] PROGMEM = R"HTML(
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>REVEN Wi-Fi Setup</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#111;color:#eee;padding:24px;max-width:520px;margin:auto}
input,button{box-sizing:border-box;width:100%;font:inherit;padding:12px;margin:7px 0;border-radius:8px;border:1px solid #555;background:#1d1d1d;color:#fff}
button{background:#2477d4;border:0;font-weight:700}.note{color:#aaa;font-size:14px}
</style></head><body>
<h1>REVEN Wi-Fi Setup</h1>
<p>XIAO ESP32-S3 is alive.</p>
<p>Enter the Wi-Fi network you want REVEN to join. The credentials are stored on the board, not in the firmware source.</p>
<form method="post" action="/save">
<label>Wi-Fi name</label><input name="ssid" maxlength="32" required autocomplete="off">
<label>Password</label><input name="pass" type="password" maxlength="64" autocomplete="new-password">
<button type="submit">Save &amp; Connect</button>
</form>
<p class="note">If the saved Wi-Fi cannot be reached, REVEN falls back to this setup network automatically.</p>
</body></html>)HTML";

static void startSetupAp() {
  WiFi.mode(WIFI_AP_STA);
  setupApActive = WiFi.softAP(SETUP_WIFI_NAME, SETUP_WIFI_PASS, 6, 0, 4);
  WiFi.setSleep(false);
  if (setupApActive) {
    Serial.print("SETUP AP READY ");
    Serial.println(WiFi.softAPIP());
  } else {
    Serial.println("SETUP AP FAIL");
  }
}

static bool connectSavedWifi() {
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  if (ssid.length() == 0) {
    Serial.println("WIFI NOT CONFIGURED");
    return false;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  Serial.print("WIFI CONNECTING ");
  Serial.println(ssid);
  WiFi.begin(ssid.c_str(), pass.c_str());

  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    stationConnected = true;
    Serial.print("WIFI CONNECTED ");
    Serial.println(WiFi.localIP());
    return true;
  }

  Serial.println("WIFI CONNECT FAIL - STARTING SETUP AP");
  WiFi.disconnect(false, false);
  return false;
}

static void configureWebServer() {
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html", PAGE);
  });

  server.on("/health", HTTP_GET, []() {
    String state = stationConnected ? "WIFI_CONNECTED " + WiFi.localIP().toString()
                                    : "SETUP_AP " + WiFi.softAPIP().toString();
    server.send(200, "text/plain", "REVEN RECOVERY OK\n" + state);
  });

  server.on("/save", HTTP_POST, []() {
    String ssid = server.arg("ssid");
    String pass = server.arg("pass");
    ssid.trim();
    if (ssid.length() == 0 || ssid.length() > 32 || pass.length() > 64) {
      server.send(400, "text/plain", "Invalid Wi-Fi settings. Return and try again.");
      return;
    }

    prefs.putString("ssid", ssid);
    prefs.putString("pass", pass);
    server.send(200, "text/html",
      "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
      "<body style='font-family:sans-serif;padding:24px'><h1>Saved</h1>"
      "<p>REVEN is restarting and will connect to your Wi-Fi.</p></body>");
    Serial.println("WIFI SETTINGS SAVED - RESTARTING");
    delay(1200);
    ESP.restart();
  });

  server.begin();
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("REVEN BOOT");

  prefs.begin("reven-wifi", false);
  if (!connectSavedWifi()) {
    startSetupAp();
  }

  configureWebServer();
  if (stationConnected) {
    Serial.print("WEB READY http://");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WEB READY http://192.168.4.1");
  }
  Serial.println("FC WAITING - recovery build does not start USB host");
}

void loop() {
  server.handleClient();
  delay(2);
}
