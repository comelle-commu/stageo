// Dashboard interne V1 (voir docs plan d'exécution §12) - rendu
// entièrement côté serveur : la clé secrète Supabase ne quitte jamais ce
// fichier, contrairement à un dashboard qui interrogerait Supabase
// directement depuis le navigateur. Pas de framework, pas de librairie de
// graphiques - des tableaux HTML, uniquement ce qui aide à décider.
//
// Volontairement pas un vrai système de comptes : protégé par un jeton
// partagé simple (variable d'environnement ADMIN_TOKEN, comparée à
// ?key=... dans l'URL) - suffisant tant que c'est la seule personne à y
// accéder, mais PAS un vrai contrôle d'accès. Ne jamais partager ce lien
// publiquement. Si ADMIN_TOKEN n'est pas configuré, l'accès est refusé
// par défaut (jamais ouvert par erreur de configuration).
//
// Variables d'environnement requises :
//   SUPABASE_URL, SUPABASE_SECRET_KEY - comme les autres fonctions
//   ADMIN_TOKEN                        - jeton choisi par vous, long et
//                                         aléatoire (ex. généré avec
//                                         `openssl rand -hex 24`)
//
// Route : /api/admin-stats?key=VOTRE_JETON

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  if (!env.ADMIN_TOKEN || url.searchParams.get("key") !== env.ADMIN_TOKEN) {
    return new Response("Accès refusé.", { status: 403, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secretKey) {
    return new Response("Configuration serveur incomplète.", { status: 500 });
  }

  const headers = { apikey: secretKey, Authorization: `Bearer ${secretKey}` };
  const sb = (path) => fetch(`${supabaseUrl}/rest/v1/${path}`, { headers }).then((r) => (r.ok ? r.json() : []));
  const sbCount = (path) =>
    fetch(`${supabaseUrl}/rest/v1/${path}`, { method: "HEAD", headers: { ...headers, Prefer: "count=exact" } }).then((r) => {
      const range = r.headers.get("content-range");
      return range ? Number(range.split("/")[1]) || 0 : 0;
    });

  const now = new Date();
  const iso = (d) => d.toISOString();
  const d7 = iso(new Date(now - 7 * 86400000));
  const d30 = iso(new Date(now - 30 * 86400000));
  const today = iso(now).slice(0, 10);

  const [
    alertsTotal,
    alerts7d,
    alerts30d,
    events30d,
    activesRows,
    premiumRows,
    boostRows,
    prospectsRows,
    contactRows,
  ] = await Promise.all([
    sbCount("criteres_parents?select=email"),
    sbCount(`criteres_parents?select=email&created_at=gte.${d7}`),
    sbCount(`criteres_parents?select=email&created_at=gte.${d30}`),
    // Plafonné à 5000 lignes : volume attendu encore faible - suffisant
    // pour agréger côté fonction sans avoir besoin d'une vue SQL dédiée.
    sb(`events?select=event_name,session_id,activite_id,organizer_id,properties,created_at&created_at=gte.${d30}&order=created_at.desc&limit=5000`),
    sb("activites?select=id,nom_activite,commune,organisateur"),
    sb("organismes_premium?select=source_key,mis_en_avant_jusquau,mise_en_avant_complete"),
    sb("activites_boost?select=activite_id,boost_jusquau"),
    sb("organizer_prospects?select=status"),
    sb("contact_requests?select=offre,created_at&offre=not.is.null"),
  ]);

  const searches = events30d.filter((e) => e.event_name === "SEARCH_PERFORMED");
  const searches7d = searches.filter((e) => e.created_at >= d7);
  const views = events30d.filter((e) => e.event_name === "ACTIVITY_VIEWED");
  const clicks = events30d.filter((e) => e.event_name === "OUTBOUND_REGISTRATION_CLICK");

  const activitesById = Object.fromEntries(activesRows.map((a) => [a.id, a]));

  const topCount = (arr, keyFn, limit = 8) => {
    const counts = new Map();
    arr.forEach((item) => {
      const k = keyFn(item);
      if (k == null || k === "") return;
      counts.set(k, (counts.get(k) || 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit);
  };

  const topCommunes = topCount(searches, (e) => e.properties && e.properties.commune);
  const topAges = topCount(searches, (e) => e.properties && e.properties.age);
  const topTypes = topCount(searches, (e) => e.properties && e.properties.type);

  // Recherches sans résultat, groupées par (commune, type, âge) - voir
  // "Opportunités de marché" §13 du plan d'exécution.
  const zeroResultKey = (e) => {
    const p = e.properties || {};
    if (p.resultats !== 0) return null;
    return [p.commune || "?", p.type || "?", p.age || "?", p.periode || "?"].join(" · ");
  };
  const zeroResults = topCount(searches, zeroResultKey, 12);

  const topViewed = topCount(views, (e) => e.activite_id, 10).map(([id, n]) => [activitesById[id], n]);
  const topClicked = topCount(clicks, (e) => e.activite_id, 10).map(([id, n]) => [activitesById[id], n]);
  const totalViews = views.length;
  const totalClicks = clicks.length;
  const ctr = totalViews ? ((totalClicks / totalViews) * 100).toFixed(1) : "—";

  const topOrganizers = topCount(clicks, (e) => e.organizer_id, 10);

  const activeBoosts = boostRows.filter((b) => b.boost_jusquau >= today).length;
  const activePartners = premiumRows.filter((p) => p.mis_en_avant_jusquau >= today && p.mise_en_avant_complete).length;
  const activePriorityOnly = premiumRows.filter((p) => p.mis_en_avant_jusquau >= today && !p.mise_en_avant_complete).length;

  const prospectCounts = {};
  prospectsRows.forEach((p) => { prospectCounts[p.status] = (prospectCounts[p.status] || 0) + 1; });

  const boostRequests = contactRows.filter((c) => c.offre === "boost").length;
  const partenaireRequests = contactRows.filter((c) => c.offre === "partenaire").length;

  const html = renderPage({
    alertsTotal, alerts7d, alerts30d,
    searchesCount: searches.length, searches7dCount: searches7d.length,
    topCommunes, topAges, topTypes, zeroResults,
    topViewed, topClicked, totalViews, totalClicks, ctr,
    topOrganizers,
    activeBoosts, activePartners, activePriorityOnly,
    prospectCounts, boostRequests, partenaireRequests,
  });

  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function table(rows, cols) {
  if (!rows.length) return '<p class="empty">Pas encore de données.</p>';
  return (
    "<table><thead><tr>" + cols.map((c) => `<th>${esc(c)}</th>`).join("") + "</tr></thead><tbody>" +
    rows.map((r) => "<tr>" + r.map((c) => `<td>${c}</td>`).join("") + "</tr>").join("") +
    "</tbody></table>"
  );
}

function renderPage(d) {
  return `<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow">
<title>Trouvéo — Dashboard interne</title>
<style>
  body{font-family:-apple-system,'Work Sans',Arial,sans-serif;background:#FFFDF8;color:#015380;margin:0;padding:32px 24px 80px;}
  .wrap{max-width:1000px;margin:0 auto;}
  h1{font-size:22px;margin:0 0 4px;}
  .sub{color:#5C7A8C;font-size:13px;margin-bottom:32px;}
  h2{font-size:16px;margin:36px 0 12px;padding-bottom:8px;border-bottom:2px solid #E7F4EE;}
  .kpis{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px;}
  .kpi{background:#fff;border:1px solid rgba(1,83,128,0.12);border-radius:12px;padding:14px 18px;min-width:140px;}
  .kpi .n{font-size:24px;font-weight:800;display:block;}
  .kpi .l{font-size:11.5px;color:#5C7A8C;}
  table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:8px;}
  th{text-align:left;font-size:11px;text-transform:uppercase;color:#93A9B5;padding:0 10px 6px 0;border-bottom:1px solid rgba(1,83,128,0.12);}
  td{padding:7px 10px 7px 0;border-bottom:1px solid rgba(1,83,128,0.06);}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:32px;}
  @media (max-width:700px){.grid2{grid-template-columns:1fr;}}
  .empty{color:#93A9B5;font-size:13px;font-style:italic;}
  .note{background:#E7F4EE;border-radius:10px;padding:10px 14px;font-size:12.5px;color:#5C7A8C;margin-top:10px;}
</style></head>
<body><div class="wrap">
  <h1>Dashboard interne Trouvéo</h1>
  <p class="sub">V1 — généré à la demande, aucune donnée mise en cache. Fenêtre : 30 derniers jours sauf mention contraire.</p>

  <h2>Audience</h2>
  <div class="kpis">
    <div class="kpi"><span class="n">${d.alertsTotal}</span><span class="l">Profils d'alerte (total)</span></div>
    <div class="kpi"><span class="n">${d.alerts7d}</span><span class="l">Nouveaux — 7 jours</span></div>
    <div class="kpi"><span class="n">${d.alerts30d}</span><span class="l">Nouveaux — 30 jours</span></div>
  </div>
  <p class="note">Visiteurs du site : voir directement le dashboard Cloudflare Web Analytics (pas accessible via cette page, jeton séparé).</p>

  <h2>Recherche</h2>
  <div class="kpis">
    <div class="kpi"><span class="n">${d.searchesCount}</span><span class="l">Recherches — 30 jours</span></div>
    <div class="kpi"><span class="n">${d.searches7dCount}</span><span class="l">Recherches — 7 jours</span></div>
  </div>
  <div class="grid2">
    <div>
      <h3>Top communes</h3>
      ${table(d.topCommunes.map(([k, n]) => [esc(k), n]), ["Commune", "Recherches"])}
    </div>
    <div>
      <h3>Top âges / types</h3>
      ${table(d.topAges.map(([k, n]) => [esc(k), n]).concat(d.topTypes.map(([k, n]) => [esc(k), n])), ["Critère", "Recherches"])}
    </div>
  </div>
  <h3>Opportunités de marché — recherches sans résultat</h3>
  <p class="note">Commune · Type · Âge · Période — triées par volume. À utiliser pour prospecter (voir plan d'exécution §12).</p>
  ${table(d.zeroResults.map(([k, n]) => [esc(k), n]), ["Recherche", "Occurrences"])}

  <h2>Activités</h2>
  <div class="kpis">
    <div class="kpi"><span class="n">${d.totalViews}</span><span class="l">Vues de fiches</span></div>
    <div class="kpi"><span class="n">${d.totalClicks}</span><span class="l">Clics vers inscription</span></div>
    <div class="kpi"><span class="n">${d.ctr}%</span><span class="l">CTR fiche → inscription</span></div>
  </div>
  <div class="grid2">
    <div>
      <h3>Top vues</h3>
      ${table(d.topViewed.filter(([a]) => a).map(([a, n]) => [esc(a.nom_activite), n]), ["Activité", "Vues"])}
    </div>
    <div>
      <h3>Top clics vers inscription</h3>
      ${table(d.topClicked.filter(([a]) => a).map(([a, n]) => [esc(a.nom_activite), n]), ["Activité", "Clics"])}
    </div>
  </div>

  <h2>Organisateurs</h2>
  ${table(d.topOrganizers.map(([k, n]) => [esc(k), n]), ["Organisateur", "Clics vers inscription"])}
  <div class="kpis" style="margin-top:16px;">
    <div class="kpi"><span class="n">${d.activeBoosts}</span><span class="l">Boosts actifs</span></div>
    <div class="kpi"><span class="n">${d.activePartners}</span><span class="l">Partenaires actifs</span></div>
    <div class="kpi"><span class="n">${d.activePriorityOnly}</span><span class="l">Anciens "Priorité" encore actifs</span></div>
  </div>
  <h3>Prospects (organizer_prospects)</h3>
  ${table(Object.entries(d.prospectCounts).map(([k, n]) => [esc(k), n]), ["Statut", "Nombre"])}

  <h2>Business</h2>
  <div class="kpis">
    <div class="kpi"><span class="n">${d.boostRequests}</span><span class="l">Demandes Boost reçues (total)</span></div>
    <div class="kpi"><span class="n">${d.partenaireRequests}</span><span class="l">Demandes Partenaire reçues (total)</span></div>
  </div>
  <p class="note">Revenu et historique des ventes : pas encore automatisés (vente manuelle, voir plan d'exécution §3) - à tenir à côté (tableur ou Table editor Supabase) tant que le volume reste faible.</p>
</div></body></html>`;
}
