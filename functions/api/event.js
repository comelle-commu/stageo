// Relais entre le tracking client (voir tracking.js) et la table
// Supabase `events` (migration 20260901b_tracking_boost_prospects.sql).
//
// Même raison d'être qu'un relais serveur que contact-request.js/
// brevo-signup.js : la clé secrète Supabase ne doit jamais être envoyée
// au navigateur.
//
// Variables d'environnement requises (Cloudflare Pages → Settings →
// Environment variables) :
//   SUPABASE_URL         - même valeur que dans scrapers/.env
//   SUPABASE_SECRET_KEY   - idem (clé secrète, PAS la clé publique côté client)
//
// Route : fichier functions/api/event.js -> disponible sur /api/event
//
// Contrat volontairement strict (voir docs plan d'exécution §6/§8) :
//   - liste blanche d'événements, rien d'autre n'est accepté ;
//   - aucune donnée personnelle acceptée (pas d'email, pas de nom) -
//     le payload est tronqué/filtré plutôt que de faire confiance au
//     client ;
//   - échoue toujours silencieusement côté navigateur (voir tracking.js,
//     sendBeacon ne lit jamais la réponse) - le tracking ne doit jamais
//     faire échouer le parcours utilisateur.

const VALID_EVENTS = new Set([
  "SEARCH_PERFORMED",
  "ACTIVITY_VIEWED",
  "OUTBOUND_REGISTRATION_CLICK",
  "ALERT_CREATED",
  "BOOST_CTA_CLICKED",
  "BOOST_PURCHASED",
]);

// Clés interdites dans `properties`, même si le client les envoie par
// erreur - filet de sécurité en plus de la discipline côté client
// (tracking.js n'envoie jamais ces champs).
const FORBIDDEN_PROPERTY_KEYS = new Set(["email", "ip", "nom", "prenom", "phone", "telephone"]);

const SESSION_ID_RE = /^[a-zA-Z0-9_-]{8,64}$/;
const MAX_PROPERTIES_JSON_LENGTH = 2000;

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

  const { event_name, session_id, activite_id, organizer_id, properties } = body || {};

  if (!VALID_EVENTS.has(event_name)) {
    return jsonResponse(400, { error: "Événement inconnu." });
  }
  if (typeof session_id !== "string" || !SESSION_ID_RE.test(session_id)) {
    return jsonResponse(400, { error: "session_id invalide." });
  }

  let cleanProps = {};
  if (properties && typeof properties === "object" && !Array.isArray(properties)) {
    for (const [key, value] of Object.entries(properties)) {
      if (FORBIDDEN_PROPERTY_KEYS.has(key.toLowerCase())) continue;
      if (value == null) continue;
      if (typeof value === "string") cleanProps[key] = value.slice(0, 200);
      else if (typeof value === "number" || typeof value === "boolean") cleanProps[key] = value;
      // objets/tableaux imbriqués ignorés : le tracking reste plat par design
    }
  }
  if (JSON.stringify(cleanProps).length > MAX_PROPERTIES_JSON_LENGTH) {
    cleanProps = {}; // mieux vaut un événement sans détail qu'un payload refusé
  }

  const row = {
    event_name,
    session_id,
    properties: cleanProps,
    activite_id: Number.isInteger(activite_id) ? activite_id : null,
    organizer_id: typeof organizer_id === "string" ? organizer_id.slice(0, 200) : null,
  };

  try {
    const res = await fetch(`${supabaseUrl}/rest/v1/events`, {
      method: "POST",
      headers: {
        apikey: secretKey,
        Authorization: `Bearer ${secretKey}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify([row]),
    });

    if (res.status === 201 || res.status === 204) {
      return jsonResponse(200, { ok: true });
    }
    const details = await res.text().catch(() => "");
    console.error("Réponse Supabase inattendue", res.status, details);
    return jsonResponse(502, { error: "Échec d'enregistrement." });
  } catch (err) {
    console.error("Appel à Supabase impossible", err);
    return jsonResponse(502, { error: "Échec d'enregistrement." });
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
