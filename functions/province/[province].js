// Pages "province" pour le référencement (SEO programmatique), en
// complément des pages ville (voir functions/stages/[commune].js) : les
// pages ville ne couvrent que 10 communes précises, alors qu'on a des
// activités dans une centaine de communes différentes. Les pages province
// couvrent tout le catalogue d'un coup (6 pages -> ~95% des activités
// avec une commune connue), même les petites communes qui n'auront
// jamais leur propre page dédiée.
//
// Rendu entièrement côté serveur, même principe que les pages ville :
// contenu réel dans le HTML dès la première réponse, pas de fetch
// client. Clé Supabase publique (même lecture publique que activites.html
// et les pages ville) - aucune variable d'environnement nécessaire.
//
// PROVINCE_OF est une copie de la table du même nom dans activites.html
// (même source : Wikipedia "Liste des communes de la Région wallonne" +
// les 19 communes de Bruxelles-Capitale) - à maintenir en synchro si l'une
// des deux évolue, pas d'import partagé possible entre une page statique
// et une Function.
//
// Route : fichier functions/province/[province].js -> disponible sur
// /province/:province.

const SUPABASE_URL = "https://oitmxxrurvutazuqsjbl.supabase.co";
const SUPABASE_KEY = "sb_publishable_BO_qv6_PsRrAP6VoVXYq7w_YoT2CfLG";

const PROVINCES = {
  "liege": { display: "Liège", label: "la province de Liège", withDe: "de la province de Liège" },
  "hainaut": { display: "Hainaut", label: "le Hainaut", withDe: "du Hainaut" },
  "namur": { display: "Namur", label: "la province de Namur", withDe: "de la province de Namur" },
  "brabant-wallon": { display: "Brabant wallon", label: "le Brabant wallon", withDe: "du Brabant wallon" },
  "luxembourg": { display: "Luxembourg", label: "la province de Luxembourg", withDe: "de la province de Luxembourg" },
  "bruxelles": { display: "Bruxelles", label: "la Région de Bruxelles-Capitale", withDe: "de la Région de Bruxelles-Capitale" },
};

// Villes ayant leur propre page dédiée (voir functions/stages/[commune].js),
// groupées par province - pour le maillage interne province <-> ville.
const CITY_PAGES_BY_PROVINCE = {
  "Liège": [["liege", "Liège"], ["herstal", "Herstal"]],
  "Hainaut": [["mons", "Mons"], ["charleroi", "Charleroi"]],
  "Brabant wallon": [["wavre", "Wavre"], ["nivelles", "Nivelles"]],
  "Bruxelles": [["uccle", "Uccle"], ["woluwe-saint-pierre", "Woluwe-Saint-Pierre"], ["woluwe-saint-lambert", "Woluwe-Saint-Lambert"], ["etterbeek", "Etterbeek"]],
  "Namur": [],
  "Luxembourg": [],
};

// Copie de PROVINCE_OF (activites.html) - voir le commentaire en tête de
// fichier.
const PROVINCE_OF = {
  'Ans': 'Liège', 'Anthisnes': 'Liège', 'Aubel': 'Liège', 'Awans': 'Liège',
  'Braives': 'Liège', 'Chaudfontaine': 'Liège', 'Comblain-au-Pont': 'Liège',
  'Engis': 'Liège', 'Esneux': 'Liège', 'Faimes': 'Liège',
  'Fexhe-le-Haut-Clocher': 'Liège', 'Geer': 'Liège', 'Grace-Hollogne': 'Liège',
  'Henri-Chapelle': 'Liège', 'Herbesthal': 'Liège', 'Heron': 'Liège',
  'Herstal': 'Liège', 'Herve': 'Liège', 'Heusy': 'Liège', 'Huy': 'Liège',
  'Jalhay': 'Liège', 'La Calamine': 'Liège', 'Liege': 'Liège', 'Liège': 'Liège',
  'Marchin': 'Liège', 'Nandrin': 'Liège', 'Neupre': 'Liège', 'Olne': 'Liège',
  'Saint-Georges-sur-Meuse': 'Liège', 'Seraing': 'Liège', 'Spa': 'Liège',
  'Sprimont': 'Liège', 'Stavelot': 'Liège', 'Tiège': 'Liège', 'Trooz': 'Liège',
  'Verviers': 'Liège', 'Waremme': 'Liège', 'Welkenraedt': 'Liège',
  'Hannut': 'Liège', 'Ferrieres': 'Liège',
  'Ath': 'Hainaut', 'Beaumont': 'Hainaut', 'Beloeil': 'Hainaut',
  'Charleroi': 'Hainaut', 'Enghien': 'Hainaut', 'Estaimpuis': 'Hainaut',
  'Forchies': 'Hainaut', 'Gosselies': 'Hainaut', 'Jurbise': 'Hainaut',
  'Loverval': 'Hainaut', 'Mons': 'Hainaut', 'Mouscron': 'Hainaut',
  'Quevaucamps': 'Hainaut', 'Saint-Ghislain': 'Hainaut', 'Tournai': 'Hainaut',
  'La Louviere': 'Hainaut', 'Silly': 'Hainaut',
  'Champion': 'Namur', 'Dinant': 'Namur', 'Eghezée': 'Namur', 'Erpent': 'Namur',
  'Fernelmont': 'Namur', 'Floreffe': 'Namur', 'Florennes': 'Namur',
  'Gedinne': 'Namur', 'Gembloux': 'Namur', 'Jambes': 'Namur', 'Lonzée': 'Namur',
  'Mettet': 'Namur', 'Namur': 'Namur', 'Ohey': 'Namur', 'Ciney': 'Namur',
  "Braine-l'Alleud": 'Brabant wallon', 'Louvain-la-Neuve': 'Brabant wallon',
  'Nivelles': 'Brabant wallon', 'Ottignies-Louvain-la-Neuve': 'Brabant wallon',
  'Waterloo': 'Brabant wallon', 'Wavre': 'Brabant wallon',
  'Bierges': 'Brabant wallon', 'Grez-Doiceau': 'Brabant wallon',
  'Arlon': 'Luxembourg', 'Bastogne': 'Luxembourg', 'Etalle': 'Luxembourg',
  'Habay-la-Neuve': 'Luxembourg', 'Libramont': 'Luxembourg',
  'Marche-en-Famenne': 'Luxembourg', 'Rouvroy': 'Luxembourg', 'Aubange': 'Luxembourg',
  'Etterbeek': 'Bruxelles', 'Forest': 'Bruxelles', 'Ixelles': 'Bruxelles',
  'Laeken': 'Bruxelles', 'Schaerbeek': 'Bruxelles', 'Uccle': 'Bruxelles',
  'Wol.-St-Lambert': 'Bruxelles', 'Wol.-St-Pierre': 'Bruxelles',
  'Auderghem': 'Bruxelles', 'Jette': 'Bruxelles',
  '1000': 'Bruxelles', '1020': 'Bruxelles', '1120': 'Bruxelles', '1130': 'Bruxelles',
};

const MOIS = { janvier: 0, février: 1, fevrier: 1, mars: 2, avril: 3, mai: 4, juin: 5, juillet: 6, août: 7, aout: 7, septembre: 8, octobre: 9, novembre: 10, décembre: 11, decembre: 11 };

const MAX_CARDS = 150;

export async function onRequestGet(context) {
  const slug = String(context.params.province || "").toLowerCase();
  const province = PROVINCES[slug];
  if (!province) {
    return new Response(render404(), { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } });
  }

  let rows = [];
  try {
    rows = await fetchAllActivites();
  } catch (err) {
    console.error("Appel Supabase impossible", err);
  }

  const matched = rows.filter((r) => provinceOf(r.commune) === province.display);
  if (!matched.length) {
    return new Response(render404(), { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } });
  }

  const upcoming = matched.filter((r) => !isPast(r));
  const past = matched.filter((r) => isPast(r));
  const ordered = upcoming.concat(past);
  const shown = ordered.slice(0, MAX_CARDS);

  const html = renderPage(slug, province, matched.length, upcoming.length, shown);
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
}

async function fetchAllActivites() {
  const PAGE = 1000;
  const pages = await Promise.all(
    [0, 1, 2].map((i) =>
      fetch(`${SUPABASE_URL}/rest/v1/activites?select=*&offset=${i * PAGE}&limit=${PAGE}`, {
        headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` },
      }).then((r) => (r.ok ? r.json() : []))
    )
  );
  return pages.flat();
}

function provinceOf(commune) {
  const base = (commune || "").replace(/\s+Extrascolaire$/i, "").replace(/\s+Parascolaire$/i, "").trim();
  return PROVINCE_OF[base] || null;
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

function ageLabel(row) {
  const a = row.age_min, b = row.age_max;
  if (a == null && b == null) return null;
  if (a != null && b != null) return a + "–" + b + " ans";
  if (a != null) return "à partir de " + a + " ans";
  return "jusqu’à " + b + " ans";
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

function renderCityLinks(display) {
  const cities = CITY_PAGES_BY_PROVINCE[display] || [];
  if (!cities.length) return "";
  const links = cities.map(([slug, name]) => `<a href="/stages/${slug}" class="neighbour-link">${esc(name)}</a>`).join("");
  return `<section class="neighbours"><h2>Villes avec leur propre page</h2>${links}</section>`;
}

function renderOtherProvinces(currentSlug) {
  return Object.entries(PROVINCES)
    .filter(([slug]) => slug !== currentSlug)
    .map(([slug, p]) => `<a href="/province/${slug}" class="neighbour-link">${esc(p.display)}</a>`)
    .join("");
}

function renderItemListSchema(slug, province, rows) {
  const items = rows.slice(0, 100).map((r, i) => ({
    "@type": "ListItem",
    position: i + 1,
    name: r.nom_activite,
    url: r.lien_source || `https://trouveo.be/province/${slug}`,
  }));
  const schema = { "@context": "https://schema.org", "@type": "ItemList", name: `Stages et activités pour enfants en ${province.display}`, itemListElement: items };
  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Accueil", item: "https://trouveo.be/" },
      { "@type": "ListItem", position: 2, name: "Toutes les activités", item: "https://trouveo.be/activites" },
      { "@type": "ListItem", position: 3, name: province.display, item: `https://trouveo.be/province/${slug}` },
    ],
  };
  return `<script type="application/ld+json">${JSON.stringify(schema)}</script>\n<script type="application/ld+json">${JSON.stringify(breadcrumb)}</script>`;
}

function renderPage(slug, province, total, upcomingCount, shownRows) {
  const title = `Stages et activités pour enfants en ${province.display} | Trouvéo`;
  const description = `${total} stage${total > 1 ? "s" : ""} et activité${total > 1 ? "s" : ""} de vacances pour enfants recensé${total > 1 ? "s" : ""} dans ${province.label}, toutes communes confondues, mis à jour en continu par Trouvéo. Alerte gratuite dès qu'une place correspond à votre enfant.`;
  const canonical = `https://trouveo.be/province/${slug}`;
  const cards = shownRows.map(renderCard).join("");
  const truncated = total > shownRows.length;

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
${renderItemListSchema(slug, province, shownRows)}
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
  .truncate-note{background:var(--mint);border-radius:14px;padding:14px 18px;font-size:14px;color:var(--ink-soft);margin:24px 0;}
  .truncate-note a{color:var(--teal-deep);font-weight:700;}
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
  .neighbours{padding:0 0 40px;}
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
    <span class="eyebrow">${esc(province.display)}</span>
    <h1>Stages et activités de vacances pour enfants en ${esc(province.display)}</h1>
    <p class="lead">${total} activité${total > 1 ? "s" : ""} repérée${total > 1 ? "s" : ""} dans ${esc(province.label)}, toutes communes confondues, dont ${upcomingCount} à venir. Trouvéo suit en continu les communes, ASBL et organismes de Wallonie et de Bruxelles pour ne rien vous faire manquer.</p>
    <p class="lead">Pas le temps de vérifier vous-même ? <a href="/criteres.html" style="color:var(--teal-deep);font-weight:700;">Créez une alerte gratuite</a> et recevez un email dès qu'un stage correspond à votre enfant.</p>
  </header>

  ${truncated ? `<div class="truncate-note">Cette page affiche les ${shownRows.length} activités les plus proches. <a href="/activites?province=${encodeURIComponent(province.display)}">Voir les ${total} activités ${esc(province.withDe)} avec les filtres complets →</a></div>` : ""}

  <div class="grid">${cards}</div>

  <section class="final">
    <h2>Envie de voir plus large ?</h2>
    <p>Retrouvez toutes les activités de Wallonie et Bruxelles, avec filtres par âge, type et rayon de recherche.</p>
    <a href="/activites" class="nav-cta">Voir toutes les activités →</a>
  </section>

  ${renderCityLinks(province.display)}

  <section class="neighbours">
    <h2>Autres provinces</h2>
    ${renderOtherProvinces(slug)}
  </section>
</div>

<footer>
  <div class="wrap">
    <p>Trouvéo — service indépendant, non affilié aux communes référencées.</p>
    <p><a href="/faq.html">FAQ</a> · <a href="/confidentialite.html">Confidentialité</a> · <a href="/mentions-legales.html">Mentions légales</a> · <a href="/cgu-cgv.html">Conditions générales</a> · <a href="/">← Retour à l'accueil</a></p>
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
    <p style="color:#5C7A8C;margin:14px 0 24px;">Aucune activité recensée pour cette province pour le moment.</p>
    <a href="/activites" style="display:inline-block;background:#0197AF;color:#fff;font-weight:700;padding:12px 24px;border-radius:100px;text-decoration:none;">Voir toutes les activités</a>
  </div>
</body>
</html>`;
}
