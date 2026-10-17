// Site configuration. Edit on the server (or template from env in provisioning); no build step.
// SGL_DOMAIN: the site's domain; every URL below derives from it (override any one if needed).
// auth0ClientId: the "Gator Pass Web" Single Page Application in Auth0 (not the Native device-flow app).
// Auth0 callback / logout URL: https://<domain>/ (the www host redirects to the apex).
const SGL_DOMAIN = "gatorcamp.us";
window.SGL_CONFIG = {
  domain: SGL_DOMAIN,
  apiBase: "https://api." + SGL_DOMAIN,
  auth0Domain: "login." + SGL_DOMAIN,
  auth0ClientId: "REPLACE_WITH_SPA_CLIENT_ID",
  audience: "https://api." + SGL_DOMAIN,
  playAddress: "play." + SGL_DOMAIN + ":7777",
};
// Local development: python3 -m http.server 5173 in server/web/ and an API on :8000
// (another port: open any page once with ?api=http://127.0.0.1:8077, it is remembered).
if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
  const q = new URLSearchParams(location.search).get("api");
  if (q) localStorage.setItem("sglApiBase", q);
  window.SGL_CONFIG.apiBase = localStorage.getItem("sglApiBase") || "http://127.0.0.1:8000";
}
