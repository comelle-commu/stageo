// Relais entre le formulaire de criteres.html ("vos critères de
// recherche") et la table Supabase `criteres_parents`.
//
// Même raison d'être qu'un relais serveur que brevo-signup.js/
// contact-request.js : la clé secrète Supabase ne doit jamais être
// envoyée au navigateur.
//
// Variables d'environnement requises (Cloudflare Pages → Settings →
// Environment variables) :
//   SUPABASE_URL         - même valeur que dans scrapers/.env
//   SUPABASE_SECRET_KEY   - idem (clé secrète, PAS la clé publique côté client)
//
// Route : fichier functions/api/save-criteria.js -> disponible sur /api/save-criteria
//
// Upsert sur `email` (on_conflict) : une personne qui republie le
// formulaire (ex. pour ajouter un enfant) met à jour sa ligne existante
// plutôt que d'en créer une deuxième - même logique que updateEnabled
// côté Brevo pour la liste d'attente simple.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const VALID_TYPES = new Set(["Sport", "Art & créativité", "Sciences & nature", "Langues", "Multi-activités"]);
const MAX_ENFANTS = 5;

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

  const { email, enfants, commune, types_activites: typesActivites } = body || {};

  if (typeof email !== "string" || !EMAIL_RE.test(email)) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }
  if (!Array.isArray(enfants) || enfants.length === 0 || enfants.length > MAX_ENFANTS) {
    return jsonResponse(400, { error: `Merci d'indiquer entre 1 et ${MAX_ENFANTS} enfant(s).` });
  }
  for (const enfant of enfants) {
    const age = enfant && enfant.age;
    if (typeof age !== "number" || Number.isNaN(age) || age < 2 || age > 18) {
      return jsonResponse(400, { error: "Chaque âge doit être compris entre 2 et 18 ans." });
    }
  }
  if (typeof commune !== "string" || !commune.trim() || commune.trim().length > 120) {
    return jsonResponse(400, { error: "Merci d'indiquer une localité." });
  }
  const types = Array.isArray(typesActivites) ? typesActivites : [];
  if (!types.every((t) => VALID_TYPES.has(t))) {
    return jsonResponse(400, { error: "Type d'activité invalide." });
  }

  try {
    const res = await fetch(`${supabaseUrl}/rest/v1/criteres_parents?on_conflict=email`, {
      method: "POST",
      headers: {
        apikey: secretKey,
        Authorization: `Bearer ${secretKey}`,
        "Content-Type": "application/json",
        Prefer: "resolution=merge-duplicates,return=minimal",
      },
      body: JSON.stringify([
        {
          email,
          enfants: enfants.map((e) => ({ age: e.age })),
          commune: commune.trim(),
          rayon_km: 15,
          types_activites: types,
          updated_at: new Date().toISOString(),
        },
      ]),
    });

    if (res.status === 201 || res.status === 204) {
      return jsonResponse(200, { ok: true });
    }

    const details = await res.text().catch(() => "");
    console.error("Réponse Supabase inattendue", res.status, details);
    return jsonResponse(502, { error: "L'enregistrement a échoué, réessayez dans un instant." });
  } catch (err) {
    console.error("Appel à Supabase impossible", err);
    return jsonResponse(502, { error: "L'enregistrement a échoué, réessayez dans un instant." });
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
