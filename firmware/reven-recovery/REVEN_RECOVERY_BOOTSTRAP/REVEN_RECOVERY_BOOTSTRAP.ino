#include <WiFi.h>
#include <WebServer.h>

static const char *WIFI_NAME = "REVEN";
static const char *WIFI_PASS = "reven1234";
static WebServer server(80);

static const char PAGE[] PROGMEM = R"HTML(
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>REVEN Recovery</title></head><body style="font-family:sans-serif;background:#111;color:#eee;padding:24px">
<h1>REVEN Recovery</h1><p>XIAO ESP32-S3 is alive.</p><p>Wi-Fi and recovery web server are running.</p>
</body></html>)HTML";

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("REVEN BOOT");

  WiFi.mode(WIFI_AP);
  bool ok = WiFi.softAP(WIFI_NAME, WIFI_PASS, 6, 0, 4);
  WiFi.setSleep(false);
  if (ok) {
    Serial.print("WIFI READY ");
    Serial.println(WiFi.softAPIP());
  } else {
    Serial.println("WIFI FAIL");
  }

  server.on("/", []() { server.send(200, "text/html", PAGE); });
  server.on("/health", []() { server.send(200, "text/plain", "REVEN RECOVERY OK"); });
  server.begin();
  Serial.println("WEB READY http://192.168.4.1");
  Serial.println("FC WAITING - recovery build does not start USB host");
}

void loop() {
  server.handleClient();
  delay(2);
}
