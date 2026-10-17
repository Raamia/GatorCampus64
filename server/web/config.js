// Site configuration. Edit on the server (or template from env in provisioning); no build step.
// auth0ClientId: the "Gator Pass Web" Single Page Application in Auth0 (not the Native device-flow app).
window.SGL_CONFIG = {
  apiBase: "https://api.chooseyourgator.select",
  auth0Domain: "login.chooseyourgator.select",
  auth0ClientId: "REPLACE_WITH_SPA_CLIENT_ID",
  audience: "https://api.chooseyourgator.select",
  playAddress: "play.chooseyourgator.select:7777",
};
// Local development: python3 -m http.server 5173 in server/web/ and an API on :8000
// (another port: open any page once with ?api=http://127.0.0.1:8077, it is remembered).
if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
  const q = new URLSearchParams(location.search).get("api");
  if (q) localStorage.setItem("sglApiBase", q);
  window.SGL_CONFIG.apiBase = localStorage.getItem("sglApiBase") || "http://127.0.0.1:8000";
}
