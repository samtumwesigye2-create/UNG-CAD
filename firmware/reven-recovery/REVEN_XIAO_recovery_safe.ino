// REVEN_XIAO recovery-safe variant.
// Keeps REVEN Wi-Fi and diagnostics alive before camera and USB-host startup.
// NOTE: this source mirrors the uploaded REVEN_XIAO.ino but defers FC USB-host takeover.

#include <WiFi.h>
#include <Preferences.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#include "reven_core.h"
#include "fc_usb.h"
#include "web_page.h"

static const char *WIFI_NAME = "REVEN";
static const char *WIFI_PASS = "reven1234";
static const uint32_t RECOVERY_GRACE_MS = 30000;

using namespace reven;
static Flight flight;
static Telemetry tele;
static MspParser parser;
static Preferences prefs;
static SemaphoreHandle_t lock;
static httpd_handle_t web = nullptr, cam = nullptr;
static int wsFds[4] = {-1, -1, -1, -1};
static uint32_t lastFcFrame = 0, lastFrames = 0;
static bool cameraReady = false;

// The unchanged camera, HTTP/WebSocket, and 50 Hz flight-loop functions from
// REVEN_XIAO.ino belong above setup() in the complete project. This file records
// the recovery-safe startup sequence to apply to that source.

static void startFlightControllerHost() {
  Serial.println("FC HOST START");
  fcusb::begin();
}

static void fcHostDelayTask(void *) {
  Serial.println("FC WAITING");
  vTaskDelay(pdMS_TO_TICKS(RECOVERY_GRACE_MS));
  startFlightControllerHost();
  vTaskDelete(nullptr);
}

void setup() {
  Serial.begin(115200);
  delay(1200);
  Serial.println("REVEN BOOT");

  lock = xSemaphoreCreateMutex();
  prefs.begin("reven", false);
  flight.cfg.hoverThrottle = prefs.getFloat("hover", 1480);
  flight.begin();

  WiFi.mode(WIFI_AP);
  bool wifiOk = WiFi.softAP(WIFI_NAME, WIFI_PASS, 6, 0, 4);
  WiFi.setSleep(false);
  if (wifiOk) {
    Serial.print("WIFI READY ");
    Serial.println(WiFi.softAPIP());
  } else {
    Serial.println("WIFI FAIL");
  }

  cameraReady = cameraBegin();
  Serial.println(cameraReady ? "CAMERA READY" : "CAMERA FAIL");

  webBegin();
  Serial.println("WEB READY http://192.168.4.1");

  xTaskCreatePinnedToCore(flightTask, "flight", 6144, nullptr, 10, nullptr, 1);
  xTaskCreatePinnedToCore(fcHostDelayTask, "fcDelay", 3072, nullptr, 4, nullptr, 0);
}

void loop() { vTaskDelay(pdMS_TO_TICKS(1000)); }
