// Désinscription "un clic" - lien présent dans chaque email transactionnel
// (criteres_alertes.py, relance_criteres.py, relance_organisateurs.py) et
// promis par confidentialite.html.
//
// GET /api/desinscription?email=... (jamais POST : ce lien est cliqué
// directement depuis un client mail, qui ne fait que des GET).
//
// Deux effets, tous deux best-effort indépendants l'un de l'autre :
//   1. Insertion dans `email_opt_out` (Supabase) - source unique consultée
//      par les scripts d'envoi avant chaque relance/alerte.
//   2. `emailBlacklisted: true` côté Brevo, si l'adresse y a un contact
//      (liste d'attente ou digest hebdomadaire, envoyé par API Campagnes) -
//      sans ça, la désinscription ne couvrirait pas le digest.
//
// Variables d'environnement requises (mêmes que save-criteria.js) :
//   SUPABASE_URL, SUPABASE_SECRET_KEY, BREVO_API_KEY (ce dernier optionnel :
//   sans lui, seul l'opt-out Supabase est enregistré, ce qui suffit déjà à
//   arrêter tous les envois transactionnels).

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const email = (url.searchParams.get("email") || "").trim().toLowerCase();

  if (!EMAIL_RE.test(email)) {
    return htmlResponse(400, errorPage("Adresse email invalide."));
  }

  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secretKey) {
    console.error("SUPABASE_URL ou SUPABASE_SECRET_KEY manquant dans les variables d'environnement Cloudflare");
    return htmlResponse(500, errorPage("Configuration serveur incomplète, réessayez plus tard ou écrivez à hello@trouveo.be."));
  }

  try {
    const res = await fetch(`${supabaseUrl}/rest/v1/email_opt_out?on_conflict=email`, {
      method: "POST",
      headers: {
        apikey: secretKey,
        Authorization: `Bearer ${secretKey}`,
        "Content-Type": "application/json",
        Prefer: "resolution=ignore-duplicates,return=minimal",
      },
      body: JSON.stringify([{ email }]),
    });
    if (!res.ok && res.status !== 409) {
      const details = await res.text().catch(() => "");
      console.error("Réponse Supabase inattendue", res.status, details);
      return htmlResponse(502, errorPage("La désinscription a échoué, réessayez dans un instant ou écrivez à hello@trouveo.be."));
    }
  } catch (err) {
    console.error("Appel à Supabase impossible", err);
    return htmlResponse(502, errorPage("La désinscription a échoué, réessayez dans un instant ou écrivez à hello@trouveo.be."));
  }

  // Best-effort, ne doit jamais faire échouer la désinscription déjà
  // enregistrée côté Supabase (qui seule est indispensable pour couvrir
  // criteres_alertes.py / relance_criteres.py / relance_organisateurs.py).
  context.waitUntil(blacklistOnBrevo(env, email).catch((err) => {
    console.error("Blacklist Brevo impossible", err);
  }));

  return htmlResponse(200, successPage(email));
}

export async function onRequest() {
  return htmlResponse(405, errorPage("Méthode non autorisée."));
}

async function blacklistOnBrevo(env, email) {
  const apiKey = env.BREVO_API_KEY;
  if (!apiKey) return;
  const resp = await fetch(`https://api.brevo.com/v3/contacts/${encodeURIComponent(email)}`, {
    method: "PUT",
    headers: { "api-key": apiKey, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ emailBlacklisted: true }),
    signal: AbortSignal.timeout(8000),
  });
  // 404 = pas de contact Brevo pour cette adresse (ex. quelqu'un qui n'a
  // rempli que /criteres.html sans jamais s'inscrire à la liste d'attente)
  // - pas une erreur, l'opt-out Supabase seul suffit déjà dans ce cas.
  if (!resp.ok && resp.status !== 404) {
    const details = await resp.text().catch(() => "");
    throw new Error(`Brevo ${resp.status}: ${details}`);
  }
}

function esc(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const PAGE_STYLE = `
  :root{
    --cream:#FFFDF8; --mint:#E7F4EE; --paper:#FFFFFF;
    --ink:#015380; --ink-soft:#5C7A8C; --ink-faint:#93A9B5;
    --teal:#0197AF; --teal-deep:#017089;
    --line: rgba(1,83,128,0.12);
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--cream);color:var(--ink);font-family:'Work Sans',Arial,sans-serif;-webkit-font-smoothing:antialiased;}
  h1{font-family:'Grandstander',Arial,sans-serif;font-weight:700;margin:0;}
  a{color:var(--teal-deep);}
  main{min-height:60vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:40px 24px;}
  .content{max-width:440px;}
  .eyebrow{display:inline-block;font-size:12.5px;font-weight:700;color:var(--teal-deep);background:var(--mint);padding:5px 12px;border-radius:100px;margin-bottom:16px;}
  h1{font-size:clamp(24px,5vw,30px);margin-bottom:14px;}
  p{font-size:15px;line-height:1.65;color:var(--ink-soft);margin:0 0 24px;}
  .btn{display:inline-block;font-weight:700;font-size:14px;text-decoration:none;padding:12px 24px;border-radius:100px;background:var(--teal);color:#fff;}
`;

function successPage(email) {
  return `<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trouvéo — Désinscription confirmée</title><meta name="robots" content="noindex,nofollow">
<link href="https://fonts.googleapis.com/css2?family=Grandstander:wght@700;800&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>${PAGE_STYLE}</style></head><body>
<main><div class="content">
<span class="eyebrow">Désinscription confirmée</span>
<h1>${esc(email)} ne recevra plus d'emails de Trouvéo</h1>
<p>Vos critères de recherche restent enregistrés si vous revenez sur le site, mais nous ne vous enverrons plus aucune alerte ni relance. Un changement d'avis ? Écrivez à <a href="mailto:hello@trouveo.be">hello@trouveo.be</a>.</p>
<a href="/" class="btn">Retour à l'accueil</a>
</div></main>
</body></html>`;
}

function errorPage(message) {
  return `<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trouvéo — Désinscription</title><meta name="robots" content="noindex,nofollow">
<link href="https://fonts.googleapis.com/css2?family=Grandstander:wght@700;800&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>${PAGE_STYLE}</style></head><body>
<main><div class="content">
<span class="eyebrow">Erreur</span>
<h1>La désinscription n'a pas pu être enregistrée</h1>
<p>${esc(message)}</p>
<a href="/" class="btn">Retour à l'accueil</a>
</div></main>
</body></html>`;
}

function htmlResponse(statusCode, html) {
  return new Response(html, {
    status: statusCode,
    headers: { "Content-Type": "text/html; charset=UTF-8" },
  });
}
