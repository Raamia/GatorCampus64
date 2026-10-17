// Shared site code: Auth0 SPA login (Authorization Code + PKCE via auth0-spa-js), API helpers, header.
(function () {
  const C = window.SGL_CONFIG;
  const SCOPES = "openid profile email create:character read:own";
  let clientPromise = null;

  function auth0Client() {
    if (!clientPromise) {
      if (!window.auth0 || !window.auth0.createAuth0Client) {
        clientPromise = Promise.reject(new Error("auth0-spa-js did not load"));
      } else {
        clientPromise = window.auth0.createAuth0Client({
          domain: C.auth0Domain,
          clientId: C.auth0ClientId,
          cacheLocation: "localstorage",
          useRefreshTokens: true,
          authorizationParams: { audience: C.audience, scope: SCOPES, redirect_uri: location.origin + "/" },
        });
      }
    }
    return clientPromise;
  }

  // Finish a login redirect (lands on "/"), then go back to the page that started it.
  async function handleRedirect() {
    const q = new URLSearchParams(location.search);
    if (!(q.has("code") && q.has("state"))) return;
    const c = await auth0Client();
    try {
      const res = await c.handleRedirectCallback();
      const to = (res.appState && res.appState.returnTo) || "/";
      history.replaceState({}, "", to);
      if (to !== "/") location.replace(to);
    } catch (e) {
      console.error(e);
      history.replaceState({}, "", "/");
    }
  }

  async function isLoggedIn() {
    try { return await (await auth0Client()).isAuthenticated(); } catch (e) { return false; }
  }

  async function login() {
    const c = await auth0Client();
    await c.loginWithRedirect({ appState: { returnTo: location.pathname + location.search } });
  }

  async function logout() {
    const c = await auth0Client();
    c.logout({ logoutParams: { returnTo: location.origin + "/" } });
  }

  async function profile() {
    try { return await (await auth0Client()).getUser(); } catch (e) { return null; }
  }

  async function token() {
    const c = await auth0Client();
    return c.getTokenSilently();
  }

  class ApiError extends Error {
    constructor(status, detail) {
      super(typeof detail === "string" ? detail : (detail && (detail.message || detail.reason)) || "HTTP " + status);
      this.status = status;
      this.detail = detail;
    }
  }

  async function api(path, opts = {}) {
    const headers = Object.assign({}, opts.headers || {});
    if (opts.auth) headers.Authorization = "Bearer " + (await token());
    let body = opts.body;
    if (body && !(body instanceof FormData) && typeof body !== "string") {
      body = JSON.stringify(body);
      headers["Content-Type"] = "application/json";
    }
    const r = await fetch(C.apiBase + path, { method: opts.method || "GET", headers, body });
    const text = await r.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
    if (!r.ok) {
      let d = data && data.detail !== undefined ? data.detail : data;
      if (Array.isArray(d)) d = d.map((x) => x.msg).join("; ");  // FastAPI validation errors
      throw new ApiError(r.status, d);
    }
    return data;
  }

  // Tiny DOM helper: h("div", {class: "x"}, "text", child...). Strings are always text nodes.
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  async function renderHeader() {
    const slot = document.getElementById("session");
    if (!slot) return;
    slot.replaceChildren();
    if (await isLoggedIn()) {
      const u = await profile();
      slot.append(
        h("span", { class: "who" }, (u && (u.nickname || u.name)) || "Signed in"),
        h("button", { class: "btn small ghost", onclick: logout }, "Log out"),
      );
    } else {
      slot.append(h("button", { class: "btn small", onclick: login }, "Log in"));
    }
  }

  const STEP_LABELS = {
    queued: "In line",
    spec: "Reading your photos",
    face: "Drawing the face",
    build: "Building the 3D gator",
    export: "Packing for the N64",
    validate: "Checking every polygon",
    preview: "Rendering previews",
    ready: "Ready!",
    failed: "Something broke",
  };

  window.SGL = { C, api, ApiError, h, login, logout, isLoggedIn, profile, token, handleRedirect, renderHeader, STEP_LABELS };

  document.addEventListener("DOMContentLoaded", async () => {
    await handleRedirect();
    await renderHeader();
    document.dispatchEvent(new Event("sgl:ready"));
  });
})();
