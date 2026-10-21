/*
 * UNG-CAD shared front-end helper (load BEFORE the page's own scripts):
 *   <script src="/static/ung-auth.js"></script>
 *
 * 1) Dashboard token (server env UNG_CAD_DASHBOARD_TOKEN):
 *    Patches window.fetch so same-origin calls to /api/manufacturing, /api/machines,
 *    /api/jobs and /api/scenes carry "Authorization: Bearer <token>". On a 401 it asks
 *    for the token once, stores it in localStorage, calls /api/login (which also sets
 *    an HttpOnly cookie so plain download links work) and retries the request.
 *    If the server has no token configured, nothing changes.
 *
 * 2) Local bridge pairing token (printed in the bridge terminal at startup):
 *    UNG.bridgeFetch(path, init) adds "X-UNG-Bridge-Token" and asks for the token
 *    once (stored in localStorage) when the bridge answers 401.
 */
(function () {
  'use strict';

  var DASH_KEY = 'ung-cad-dashboard-token';
  var BRIDGE_KEY = 'ung-cad-bridge-token';
  var BRIDGE_URL = 'http://127.0.0.1:8765';
  var PROTECTED = ['/api/manufacturing', '/api/machines', '/api/jobs', '/api/scenes'];
  var nativeFetch = window.fetch.bind(window);
  var pendingDashPrompt = null;

  function isProtected(url) {
    try {
      var u = new URL(url, window.location.href);
      if (u.origin !== window.location.origin) {
        return false;
      }
      return PROTECTED.some(function (p) {
        return u.pathname === p || u.pathname.indexOf(p + '/') === 0;
      });
    } catch (e) {
      return false;
    }
  }

  function withHeader(init, name, value) {
    var out = Object.assign({}, init || {});
    var headers = new Headers(out.headers || {});
    if (!headers.has(name)) {
      headers.set(name, value);
    }
    out.headers = headers;
    return out;
  }

  async function login(token) {
    var r = await nativeFetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token }),
      credentials: 'same-origin'
    });
    return r.ok;
  }

  async function logout() {
    localStorage.removeItem(DASH_KEY);
    await nativeFetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
  }

  function askDashboardToken() {
    if (pendingDashPrompt) {
      return pendingDashPrompt;
    }
    pendingDashPrompt = (async function () {
      var t = window.prompt('This UNG-CAD server requires a dashboard token.\nEnter it (it is stored in this browser):');
      if (!t) {
        return null;
      }
      t = t.trim();
      if (await login(t)) {
        localStorage.setItem(DASH_KEY, t);
        return t;
      }
      window.alert('Invalid dashboard token.');
      return null;
    })();
    pendingDashPrompt.finally(function () {
      pendingDashPrompt = null;
    });
    return pendingDashPrompt;
  }

  async function apiFetch(input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || String(input);
    if (!isProtected(url)) {
      return nativeFetch(input, init);
    }
    var token = localStorage.getItem(DASH_KEY);
    var first = token ? withHeader(init, 'Authorization', 'Bearer ' + token) : (init || {});
    var r = await nativeFetch(input, first);
    if (r.status !== 401) {
      return r;
    }
    localStorage.removeItem(DASH_KEY);
    var fresh = await askDashboardToken();
    if (!fresh) {
      return r;
    }
    return nativeFetch(input, withHeader(init, 'Authorization', 'Bearer ' + fresh));
  }

  window.fetch = apiFetch;

  // Refresh the download cookie for a token stored earlier (cookie lasts 30 days).
  if (localStorage.getItem(DASH_KEY)) {
    login(localStorage.getItem(DASH_KEY)).catch(function () {});
  }

  function bridgeToken(forcePrompt) {
    var t = localStorage.getItem(BRIDGE_KEY);
    if (!t || forcePrompt) {
      t = window.prompt('Enter the pairing token shown in the UNG-CAD bridge terminal window:');
      if (!t) {
        return null;
      }
      t = t.trim();
      localStorage.setItem(BRIDGE_KEY, t);
    }
    return t;
  }

  function clearBridgeToken() {
    localStorage.removeItem(BRIDGE_KEY);
  }

  async function bridgeFetch(path, init) {
    var token = bridgeToken(false);
    if (!token) {
      throw new Error('Bridge token required (shown in the bridge terminal)');
    }
    var r = await nativeFetch(BRIDGE_URL + path, withHeader(init, 'X-UNG-Bridge-Token', token));
    if (r.status === 401) {
      clearBridgeToken();
      token = bridgeToken(true);
      if (!token) {
        return r;
      }
      r = await nativeFetch(BRIDGE_URL + path, withHeader(init, 'X-UNG-Bridge-Token', token));
    }
    return r;
  }

  window.UNG = {
    BRIDGE_URL: BRIDGE_URL,
    apiFetch: apiFetch,
    login: login,
    logout: logout,
    setDashboardToken: function (t) { localStorage.setItem(DASH_KEY, t); return login(t); },
    clearDashboardToken: function () { localStorage.removeItem(DASH_KEY); },
    bridgeFetch: bridgeFetch,
    bridgeToken: bridgeToken,
    clearBridgeToken: clearBridgeToken
  };
})();
