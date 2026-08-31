// Relais entre les deux petits formulaires de partenaires.html
// ("suggérer un organisme" et "être recontacté pour un partenariat
// premium/un encart pub") et la table Supabase `contact_requests`.
//
// Même raison d'être qu'un relais serveur (voir brevo-signup.js) : la clé
// secrète Supabase ne doit jamais être envoyée au navigateur. Cette
// fonction tourne côté serveur, écrit dans Supabase avec la clé secrète
// (qui contourne RLS, comme pour la table `activites`), la clé reste dans
// une variable d'environnement Cloudflare.
//
// Variables d'environnement requises (Cloudflare Pages → Settings →
// Environment variables) :
//   SUPABASE_URL         - même valeur que dans scrapers/.env
//   SUPABASE_SECRET_KEY   - idem (clé secrète, PAS la clé publique côté client)
//
// Route : fichier functions/api/contact-request.js -> disponible sur /api/contact-request

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const URL_RE = /^https?:\/\/[^\s]+\.[^\s]+$/i;
const VALID_TYPES = new Set(["organisme", "premium"]);

export async function onRequestPost(context) {
  const { request, env } = context;

  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secretKey) {
    console.error("SUPABASE_URL ou SUPABASE_SECRET_KEY manquant dans les variables d'environnement Cloudflare");
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(400, { error: "Requête invalide." });
  }

  const { type, email, url, message } = body || {};

  if (!VALID_TYPES.has(type)) {
    return jsonResponse(400, { error: "Type de demande invalide." });
  }
  if (email && (typeof email !== "string" || !EMAIL_RE.test(email))) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }
  if (type === "organisme") {
    if (typeof url !== "string" || !URL_RE.test(url.trim())) {
      return jsonResponse(400, { error: "Merci d'indiquer une adresse de site valide (https://...)." });
    }
  }
  if (type === "premium" && !email) {
    return jsonResponse(400, { error: "Merci d'indiquer votre email pour qu'on puisse vous recontacter." });
  }

  try {
    const res = await fetch(`${supabaseUrl}/rest/v1/contact_requests`, {
      method: "POST",
      headers: {
        apikey: secretKey,
        Authorization: `Bearer ${secretKey}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify([
        {
          type,
          email: email || null,
          url: url ? url.trim() : null,
          message: message ? String(message).slice(0, 2000) : null,
        },
      ]),
    });

    if (res.status === 201 || res.status === 204) {
      return jsonResponse(200, { ok: true });
    }

    const details = await res.text().catch(() => "");
    console.error("Réponse Supabase inattendue", res.status, details);
    return jsonResponse(502, { error: "L'envoi a échoué, réessayez dans un instant." });
  } catch (err) {
    console.error("Appel à Supabase impossible", err);
    return jsonResponse(502, { error: "L'envoi a échoué, réessayez dans un instant." });
  }
}

export async function onRequest() {
  return jsonResponse(405, { error: "Méthode non autorisée." });
}

function jsonResponse(statusCode, body) {
  return new Response(JSON.stringify(body), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}
