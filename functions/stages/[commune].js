// Pages "ville" pour le référencement (SEO programmatique) : une page par
// commune plutôt que tout miser sur /activites. Rendu entièrement côté
// serveur (pas de fetch client comme activites.html) pour que Google et
// les autres moteurs voient le vrai contenu dès la première réponse.
//
// Route : fichier functions/stages/[commune].js -> disponible sur
// /stages/:commune (routage dynamique Cloudflare Pages Functions).
//
// Clé Supabase utilisée : la clé publique (publishable), la même que
// celle déjà exposée côté client dans activites.html - la table
// `activites` est en lecture publique (RLS), donc aucune variable
// d'environnement Cloudflare n'est nécessaire pour cette fonction.
//
// Départ volontairement limité à quelques communes pilotes (voir
// PILOT_COMMUNES ci-dessous) plutôt qu'une page pour les ~110 communes
// présentes en base : mieux vaut tester avec un contenu solide sur peu de
// pages que publier d'un coup des pages fines/vides qui nuiraient au
// référencement plutôt que de l'aider. Une commune non listée renvoie un
// vrai 404 (jamais une page vide indexable).
//
// Les valeurs brutes stockées en base sont parfois incohérentes (accents,
// abréviations - ex. "Liège" et "Liege" coexistent, "Wol.-St-Pierre" pour
// Woluwe-Saint-Pierre) : dbValues couvre les variantes connues pour
// chaque commune pilote, display est le nom présenté aux visiteurs.

const SUPABASE_URL = "https://oitmxxrurvutazuqsjbl.supabase.co";
const SUPABASE_KEY = "sb_publishable_BO_qv6_PsRrAP6VoVXYq7w_YoT2CfLG";

const PILOT_COMMUNES = {
  "liege": { display: "Liège", region: "Wallonie", dbValues: ["Liège", "Liege"], provinceSlug: "liege", provinceName: "Liège" },
  "uccle": { display: "Uccle", region: "Bruxelles", dbValues: ["Uccle"], provinceSlug: "bruxelles", provinceName: "Bruxelles" },
  "woluwe-saint-pierre": { display: "Woluwe-Saint-Pierre", region: "Bruxelles", dbValues: ["Wol.-St-Pierre"], provinceSlug: "bruxelles", provinceName: "Bruxelles" },
  "woluwe-saint-lambert": { display: "Woluwe-Saint-Lambert", region: "Bruxelles", dbValues: ["Wol.-St-Lambert"], provinceSlug: "bruxelles", provinceName: "Bruxelles" },
  "etterbeek": { display: "Etterbeek", region: "Bruxelles", dbValues: ["Etterbeek"], provinceSlug: "bruxelles", provinceName: "Bruxelles" },
  "wavre": { display: "Wavre", region: "Wallonie", dbValues: ["Wavre"], provinceSlug: "brabant-wallon", provinceName: "Brabant wallon" },
  "mons": { display: "Mons", region: "Wallonie", dbValues: ["Mons"], provinceSlug: "hainaut", provinceName: "Hainaut" },
  "charleroi": { display: "Charleroi", region: "Wallonie", dbValues: ["Charleroi"], provinceSlug: "hainaut", provinceName: "Hainaut" },
  "nivelles": { display: "Nivelles", region: "Wallonie", dbValues: ["Nivelles"], provinceSlug: "brabant-wallon", provinceName: "Brabant wallon" },
  "herstal": { display: "Herstal", region: "Wallonie", dbValues: ["Herstal"], provinceSlug: "liege", provinceName: "Liège" },
};

const MOIS = { janvier: 0, février: 1, fevrier: 1, mars: 2, avril: 3, mai: 4, juin: 5, juillet: 6, août: 7, aout: 7, septembre: 8, octobre: 9, novembre: 10, décembre: 11, decembre: 11 };

export async function onRequestGet(context) {
  const slug = String(context.params.commune || "").toLowerCase();
  const commune = PILOT_COMMUNES[slug];
  if (!commune) {
    return new Response(render404(), { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } });
  }

  const filter = commune.dbValues.map((v) => encodeURIComponent(v)).join(",");
  const url = `${SUPABASE_URL}/rest/v1/activites?select=*&commune=in.(${filter})&order=nom_activite.asc&limit=300`;

  let rows = [];
  try {
    const res = await fetch(url, { headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` } });
    if (res.ok) rows = await res.json();
  } catch (err) {
    console.error("Appel Supabase impossible", err);
  }

  if (!rows.length) {
    return new Response(render404(), { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } });
  }

  const upcoming = rows.filter((r) => !isPast(r));
  const past = rows.filter((r) => isPast(r));
  const ordered = upcoming.concat(past);

  const html = renderPage(slug, commune, ordered, upcoming.length);
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
}

function lastDate(text) {
  if (!text) return null;
  const slashMatches = [...text.matchAll(/(\d{1,2})\/(\d{1,2})\/(\d{4})/g)];
  if (slashMatches.length) {
    const m = slashMatches[slashMatches.length - 1];
    return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
  }
  const wordMatches = [...text.matchAll(/(\d{1,2})\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)(?:\s+(\d{4}))?/gi)];
  if (wordMatches.length) {
    const years = [...text.matchAll(/\b(20\d{2})\b/g)].map((m) => Number(m[1]));
    const fallbackYear = years.length ? years[years.length - 1] : new Date().getFullYear();
    const m = wordMatches[wordMatches.length - 1];
    const monthKey = m[2].toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    const month = MOIS[monthKey];
    const year = m[3] ? Number(m[3]) : fallbackYear;
    if (month != null) return new Date(year, month, Number(m[1]));
  }
  return null;
}

function isPast(row) {
  const d = lastDate(row.dates);
  if (!d) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return d < today;
}

function classifyDispo(text) {
  const t = (text || "").toLowerCase();
  if (/liste\s+d[e']attente/.test(t)) return { cls: "p-wait", label: "Liste d’attente" };
  if (/places?\s+limit[ée]es?/.test(t)) return { cls: "p-wait", label: "Places limitées" };
  if (/places?\s+(?:encore\s+)?dispo/.test(t)) return { cls: "p-ok", label: "Places disponibles" };
  if (/cl[ôo]tur[ée]/.test(t)) return { cls: "p-warn", label: "Clôturé" };
  if (/(?<!semaine )\bcomplet/.test(t)) return { cls: "p-warn", label: "Complet" };
  return { cls: "p-neutral", label: "Non communiqué" };
}

// Même correctif que activites.html (voir sa version pour le contexte) :
// age_min/age_max sont parfois décimaux (ex. iclub.py, "8 an(s) et 5
// mois" -> 8.416666...) - affiché brut, illisible.
function formatAgeNum(n) {
  const y = Math.floor(n + 1e-9);
  const m = Math.round((n - y) * 12);
  if (m <= 0) return y + " an" + (y !== 1 ? "s" : "");
  if (m >= 12) return (y + 1) + " an" + (y + 1 !== 1 ? "s" : "");
  return y + " an" + (y !== 1 ? "s" : "") + " " + m + " mois";
}

function ageLabel(row) {
  const a = row.age_min, b = row.age_max;
  if (a == null && b == null) return null;
  const bothWhole = (a == null || Number.isInteger(a)) && (b == null || Number.isInteger(b));
  if (bothWhole) {
    if (a != null && b != null) return a + "–" + b + " ans";
    if (a != null) return "à partir de " + a + " ans";
    return "jusqu’à " + b + " ans";
  }
  if (a != null && b != null) return formatAgeNum(a) + " – " + formatAgeNum(b);
  if (a != null) return "à partir de " + formatAgeNum(a);
  return "jusqu’à " + formatAgeNum(b);
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderCard(r) {
  const dispo = classifyDispo(r.disponibilite);
  const age = ageLabel(r);
  const source = r.organisateur || r.commune || "Non précisé";
  const past = isPast(r);
  let html = `<article class="card${past ? " is-past" : ""}">`;
  html += '<div class="card-body">';
  if (past) html += '<div class="past-badge">Édition passée</div>';
  html += `<div class="card-source">${esc(source)}</div>`;
  html += `<div class="card-name">${esc(r.nom_activite)}</div>`;
  html += '<div class="card-meta">';
  html += `<div class="row"><span>📅 ${esc(r.dates || "Dates non précisées")}</span></div>`;
  html += `<div class="row"><span>📍 ${esc(r.lieu || r.commune || "Lieu non précisé")}</span></div>`;
  if (age) html += `<div class="row"><span>👤 ${esc(age)}</span></div>`;
  if (r.prix) html += `<div class="row"><span>💶 ${esc(r.prix)}</span></div>`;
  html += "</div></div>";
  html += `<div class="card-foot"><span class="pill ${dispo.cls}">${esc(dispo.label)}</span>`;
  if (r.lien_source) html += `<a class="card-link" href="${esc(r.lien_source)}" target="_blank" rel="noopener noreferrer">Voir la source →</a>`;
  html += "</div></article>";
  return html;
}

function renderNeighbours(currentSlug) {
  const others = Object.entries(PILOT_COMMUNES).filter(([slug]) => slug !== currentSlug);
  return others.map(([slug, c]) => `<a href="/stages/${slug}" class="neighbour-link">${esc(c.display)}</a>`).join("");
}

function renderItemListSchema(slug, commune, rows) {
  const items = rows.slice(0, 100).map((r, i) => ({
    "@type": "ListItem",
    position: i + 1,
    name: r.nom_activite,
    url: r.lien_source || `https://trouveo.be/stages/${slug}`,
  }));
  const schema = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `Stages et activités pour enfants à ${commune.display}`,
    itemListElement: items,
  };
  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Accueil", item: "https://trouveo.be/" },
      { "@type": "ListItem", position: 2, name: "Toutes les activités", item: "https://trouveo.be/activites" },
      { "@type": "ListItem", position: 3, name: commune.display, item: `https://trouveo.be/stages/${slug}` },
    ],
  };
  return `<script type="application/ld+json">${JSON.stringify(schema)}</script>\n<script type="application/ld+json">${JSON.stringify(breadcrumb)}</script>`;
}

function renderPage(slug, commune, rows, upcomingCount) {
  const total = rows.length;
  const title = `Stages et activités pour enfants à ${commune.display} | Trouvéo`;
  const description = `${total} stage${total > 1 ? "s" : ""} et activité${total > 1 ? "s" : ""} de vacances pour enfants recensé${total > 1 ? "s" : ""} à ${commune.display} (${commune.region}), mis à jour en continu par Trouvéo. Alerte gratuite dès qu'une place correspond à votre enfant.`;
  const canonical = `https://trouveo.be/stages/${slug}`;
  const cards = rows.map(renderCard).join("");

  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${esc(title)}</title>
<meta name="description" content="${esc(description)}">
<meta name="robots" content="index,follow">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="canonical" href="${canonical}">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_BE">
<meta property="og:url" content="${canonical}">
<meta property="og:site_name" content="Trouvéo">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(description)}">
<meta property="og:image" content="https://trouveo.be/og-image.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Grandstander:wght@600;700;800&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
${renderItemListSchema(slug, commune, rows)}
<style>
  :root{
    --cream:#FFFDF8; --paper:#FFFFFF; --mint:#E7F4EE; --surface-tint:#F2F7F6;
    --ink:#015380; --ink-soft:#5C7A8C; --ink-faint:#93A9B5;
    --teal:#0197AF; --teal-deep:#017089; --orange-deep:#E2A20E;
    --line:rgba(1,83,128,0.12); --line-soft:rgba(1,83,128,0.07);
    --pill-bg:#EEF3F1; --pill-ink:#5C7A8C;
    --warn-bg:#FCEAE7; --warn-ink:#C23B2E; --ok-bg:#E7F4EE; --ok-ink:#1A7A4C; --wait-bg:#FDF1E1; --wait-ink:#8A5A00;
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--cream);color:var(--ink);font-family:'Work Sans',sans-serif;-webkit-font-smoothing:antialiased;}
  h1,h2{font-family:'Grandstander',sans-serif;font-weight:700;margin:0;}
  a{color:inherit;}
  .wrap{max-width:1140px;margin:0 auto;padding:0 28px;}
  .nav-sticky{position:sticky;top:0;z-index:100;background:var(--cream);border-bottom:1px solid var(--line);}
  nav.wrap{display:flex;align-items:center;justify-content:space-between;gap:10px;padding-top:24px;padding-bottom:24px;position:relative;}
  .logo{display:flex;align-items:center;}
  .logo-img{height:58px;width:auto;display:block;}
  .nav-links{display:flex;align-items:center;gap:20px;flex:none;}
  .nav-link{font-size:14.5px;font-weight:600;color:var(--ink-soft);text-decoration:none;white-space:nowrap;}
  .nav-cta{font-size:14px;font-weight:700;padding:13px 24px;border-radius:100px;background:var(--teal);color:#fff;text-decoration:none;white-space:nowrap;box-shadow:0 10px 24px -8px rgba(1,151,175,0.5);}
  .nav-toggle{display:none;background:none;border:none;cursor:pointer;font-size:26px;line-height:1;color:var(--ink);padding:4px 6px;}
  @media (max-width:520px){
    nav.wrap{padding-top:16px;padding-bottom:16px;}
    .logo-img{height:44px;}
    .nav-toggle{display:block;}
    .nav-links{display:none;position:absolute;top:100%;left:0;right:0;flex-direction:column;align-items:stretch;gap:0;background:var(--cream);border-bottom:1px solid var(--line);padding:6px 24px 20px;box-shadow:0 12px 20px -12px rgba(1,83,128,0.15);}
    .nav-links.open{display:flex;}
    .nav-link{font-size:16px;padding:13px 0;border-bottom:1px solid var(--line);}
    .nav-cta{margin-top:14px;text-align:center;font-size:15px;padding:13px 20px;}
  }
  header.intro{padding:20px 0 30px;}
  .eyebrow{display:inline-block;font-size:12.5px;font-weight:700;color:var(--teal-deep);background:var(--mint);padding:5px 12px;border-radius:100px;margin-bottom:14px;}
  h1{font-size:clamp(26px,4vw,38px);margin-bottom:14px;}
  .lead{font-size:16px;color:var(--ink-soft);line-height:1.65;max-width:70ch;margin:0 0 8px;}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin:30px 0 50px;}
  .card{background:var(--paper);border:1px solid var(--line);border-radius:18px;box-shadow:0 12px 28px -18px rgba(1,83,128,0.3);overflow:hidden;display:flex;flex-direction:column;}
  .card.is-past{opacity:.7;}
  .past-badge{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.02em;text-transform:uppercase;color:var(--ink-faint);background:var(--pill-bg);padding:3px 10px;border-radius:100px;margin-bottom:10px;}
  .card-body{padding:18px 20px;flex:1;}
  .card-source{font-size:11.5px;font-weight:700;letter-spacing:.02em;color:var(--teal-deep);margin-bottom:8px;text-transform:uppercase;}
  .card-name{font-family:'Grandstander',sans-serif;font-weight:700;font-size:16.5px;color:var(--ink);line-height:1.3;margin-bottom:10px;}
  .card-meta{font-size:13.5px;color:var(--ink-soft);display:flex;flex-direction:column;gap:5px;}
  .card-foot{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 20px;border-top:1px solid var(--line-soft);background:var(--surface-tint);}
  .pill{font-size:11.5px;font-weight:700;padding:5px 11px;border-radius:100px;white-space:nowrap;}
  .pill.p-warn{background:var(--warn-bg);color:var(--warn-ink);}
  .pill.p-ok{background:var(--ok-bg);color:var(--ok-ink);}
  .pill.p-wait{background:var(--wait-bg);color:var(--wait-ink);}
  .pill.p-neutral{background:var(--pill-bg);color:var(--pill-ink);}
  .card-link{font-size:12.5px;font-weight:700;color:var(--teal-deep);text-decoration:none;white-space:nowrap;}
  .card-link:hover{text-decoration:underline;}
  section.final{padding:40px 0 60px;text-align:center;background:var(--mint);border-radius:24px;margin-bottom:50px;}
  section.final h2{font-size:clamp(22px,3vw,28px);margin-bottom:12px;}
  section.final p{color:var(--ink-soft);font-size:15.5px;margin-bottom:22px;max-width:52ch;margin-left:auto;margin-right:auto;}
  section.final .nav-cta{display:inline-block;}
  .neighbours{padding:0 0 60px;}
  .neighbours h2{font-size:16px;margin-bottom:14px;}
  .neighbour-link{display:inline-block;font-size:13.5px;font-weight:600;color:var(--teal-deep);background:var(--paper);border:1px solid var(--line);padding:8px 16px;border-radius:100px;text-decoration:none;margin:0 8px 8px 0;}
  .neighbour-link:hover{border-color:var(--teal);}
  footer{padding:30px 0 60px;text-align:center;font-size:13px;color:var(--ink-faint);border-top:1px solid var(--line);}
  footer a{text-decoration:underline;}
  .back-to-top{display:inline-flex;align-items:center;gap:6px;margin-top:14px;padding:9px 18px;border-radius:100px;background:var(--paper);border:1px solid var(--line);color:var(--ink-soft);font-size:13px;font-weight:600;text-decoration:none;}
</style>
</head>
<body>

<div class="nav-sticky">
<nav class="wrap">
  <a class="logo" href="/">
    <img src="/trouveo-logo.png" alt="Trouvéo" class="logo-img">
  </a>
  <button class="nav-toggle" id="navToggle" aria-label="Menu" aria-expanded="false" aria-controls="navLinks">☰</button>
  <div class="nav-links" id="navLinks">
    <a href="/activites" class="nav-link">Voir toutes les activités</a>
    <a href="/partenaires.html" class="nav-link">Pour les organisateurs</a>
    <a href="/#top-form" class="nav-cta">Recevoir des alertes</a>
  </div>
</nav>
</div>
<script>
(function(){
  var toggle = document.getElementById('navToggle');
  var links = document.getElementById('navLinks');
  if(!toggle || !links) return;
  toggle.addEventListener('click', function(){
    var isOpen = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    toggle.textContent = isOpen ? '✕' : '☰';
  });
  links.querySelectorAll('a').forEach(function(link){
    link.addEventListener('click', function(){
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.textContent = '☰';
    });
  });
})();
</script>

<div class="wrap">
  <header class="intro">
    <span class="eyebrow">${esc(commune.display)} · ${esc(commune.region)}</span>
    <h1>Stages et activités de vacances pour enfants à ${esc(commune.display)}</h1>
    <p class="lead">${total} activité${total > 1 ? "s" : ""} repérée${total > 1 ? "s" : ""} à ${esc(commune.display)} et alentours, dont ${upcomingCount} à venir. Trouvéo suit en continu les communes, ASBL et organismes de Wallonie et de Bruxelles pour ne rien vous faire manquer.</p>
    <p class="lead">Pas le temps de vérifier vous-même ? <a href="/criteres.html" style="color:var(--teal-deep);font-weight:700;">Créez une alerte gratuite</a> et recevez un email dès qu'un stage correspond à votre enfant.</p>
  </header>

  <div class="grid">${cards}</div>

  <section class="final">
    <h2>Envie de voir plus large ?</h2>
    <p>Retrouvez toutes les activités de Wallonie et Bruxelles, avec filtres par âge, type et rayon de recherche.</p>
    <a href="/activites" class="nav-cta">Voir toutes les activités →</a>
  </section>

  <section class="neighbours">
    <h2>Stages dans d'autres villes</h2>
    ${renderNeighbours(slug)}
    <a href="/province/${commune.provinceSlug}" class="neighbour-link" style="background:var(--mint);border-color:transparent;">Toutes les activités de ${esc(commune.provinceName)} →</a>
  </section>
</div>

<footer>
  <div class="wrap">
    <p>Trouvéo — service indépendant, non affilié aux communes référencées.</p>
    <p><a href="/faq.html">FAQ</a> · <a href="/confidentialite.html">Confidentialité</a> · <a href="/mentions-legales.html">Mentions légales</a> · <a href="/cgu-cgv.html">Conditions générales</a> · <a href="https://www.facebook.com/profile.php?id=61593951054331" target="_blank" rel="noopener noreferrer">Facebook</a> · <a href="/">← Retour à l'accueil</a></p>
    <p><a href="#" class="back-to-top">↑ Remonter en haut</a></p>
  </div>
</footer>

</body>
</html>`;
}

function render404() {
  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trouvéo — Page introuvable</title>
<meta name="robots" content="noindex,follow">
<link rel="icon" type="image/png" href="/favicon.png">
</head>
<body style="margin:0;background:#FFFDF8;color:#015380;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:24px;">
  <div>
    <h1 style="font-size:28px;">Cette page s'est perdue en chemin</h1>
    <p style="color:#5C7A8C;margin:14px 0 24px;">Aucune activité recensée pour cette ville pour le moment.</p>
    <a href="/activites" style="display:inline-block;background:#0197AF;color:#fff;font-weight:700;padding:12px 24px;border-radius:100px;text-decoration:none;">Voir toutes les activités</a>
  </div>
</body>
</html>`;
}
