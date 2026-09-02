// Crée une session Stripe Checkout pour Boost (29€, une activité, 4
// semaines) ou Partenaire (240€/an, un organisme) - remplace le paiement
// manuel (facture + activation à la main dans Supabase) par un paiement
// en ligne immédiat. L'activation elle-même se fait dans
// functions/api/stripe-webhook.js, une fois le paiement confirmé par
// Stripe (jamais ici : cette fonction ne fait que créer la session,
// avant tout paiement réel).
//
// Appel direct à l'API REST Stripe (pas le SDK stripe-node - ce dépôt
// n'a ni package.json ni étape de build, comme pour Brevo/Supabase
// ailleurs dans functions/, un simple fetch() suffit et reste cohérent).
//
// Variables d'environnement requises (Cloudflare Pages → Settings →
// Environment variables) :
//   STRIPE_SECRET_KEY   - clé secrète Stripe (Dashboard → Developers → API keys)
//   SUPABASE_URL / SUPABASE_SECRET_KEY - pour vérifier qu'une activité
//     à booster existe vraiment avant de créer une session de paiement
//
// Route : fichier functions/api/create-checkout-session.js -> disponible
// sur /api/create-checkout-session
//
// Vérification d'affiliation (voir metadata.verifie, lu par
// stripe-webhook.js) : rien n'empêchait jusqu'ici n'importe qui de payer
// pour booster/mettre en avant une activité qui n'est pas la sienne - pas
// de vraie fraude possible (ça ne fait de mal à personne d'autre), mais
// un badge "Partenaire"/Boost obtenu par une personne non affiliée
// viderait le badge de son sens. Plutôt que d'construire un système de
// comptes, on vérifie que l'email du paiement correspond à quelque chose
// qu'on connaît déjà pour cette activité/cet organisme (contact_email
// soumis via soumettre-activite.html, ou domaine du site source
// `lien_source`) - si rien ne correspond, le paiement est accepté quand
// même (pas de vente perdue) mais l'activation n'est pas automatique,
// voir stripe-webhook.js.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SITE_URL = "https://trouveo.be";

const OFFRES = {
  boost: { montant_cents: 2900, jours: 28 },
  partenaire: { montant_cents: 24000, jours: 365 },
};

export async function onRequestPost(context) {
  const { request, env } = context;

  const stripeKey = env.STRIPE_SECRET_KEY;
  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!stripeKey || !supabaseUrl || !secretKey) {
    console.error("STRIPE_SECRET_KEY, SUPABASE_URL ou SUPABASE_SECRET_KEY manquant dans les variables d'environnement Cloudflare");
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(400, { error: "Requête invalide." });
  }

  const { offre, email, activite_id: activiteIdRaw, organisme: organismeRaw, token } = body || {};

  if (!OFFRES[offre]) {
    return jsonResponse(400, { error: "Offre invalide." });
  }
  if (typeof email !== "string" || !EMAIL_RE.test(email)) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }

  // Un jeton "espace organisateur" valide (voir organisateur.html,
  // functions/api/organisateur-espace.js) prouve déjà l'identité - preuve
  // plus forte qu'une simple correspondance de domaine d'email, donc
  // vérifiée en premier.
  let tokenSourceKey = null;
  if (typeof token === "string" && token) {
    try {
      const res = await fetch(
        `${supabaseUrl}/rest/v1/organisateurs_contact?select=source_key&access_token=eq.${encodeURIComponent(token)}`,
        { headers: { apikey: secretKey, Authorization: `Bearer ${secretKey}` } }
      );
      const rows = await res.json();
      tokenSourceKey = Array.isArray(rows) && rows[0] ? rows[0].source_key : null;
    } catch (err) {
      console.error("Vérification du jeton organisateur impossible", err);
      // Non bloquant : retombe sur la vérification par domaine ci-dessous.
    }
  }

  let productName;
  const metadata = { offre, email };

  if (offre === "boost") {
    const activiteId = Number(activiteIdRaw);
    if (!Number.isInteger(activiteId) || activiteId <= 0) {
      return jsonResponse(400, { error: "Merci de sélectionner votre activité dans la liste." });
    }
    // Vérifie que l'activité existe vraiment (et récupère son nom pour le
    // récapitulatif Stripe) plutôt que de faire confiance à un ID envoyé
    // par le navigateur - activites_boost a une contrainte de clé
    // étrangère de toute façon, mais mieux vaut un message clair ici
    // qu'une erreur Stripe générique après coup.
    let activite;
    try {
      const res = await fetch(
        `${supabaseUrl}/rest/v1/activites?select=id,nom_activite,contact_email,lien_source,organisateur,commune&id=eq.${activiteId}`,
        { headers: { apikey: secretKey, Authorization: `Bearer ${secretKey}` } }
      );
      const rows = await res.json();
      activite = Array.isArray(rows) ? rows[0] : null;
    } catch (err) {
      console.error("Vérification de l'activité impossible", err);
      return jsonResponse(502, { error: "Impossible de vérifier cette activité, réessayez dans un instant." });
    }
    if (!activite) {
      return jsonResponse(404, { error: "Activité introuvable - merci de la sélectionner dans la liste proposée." });
    }
    productName = `Boost Trouvéo — ${activite.nom_activite}`;
    metadata.activite_id = String(activiteId);
    const ownedByToken =
      tokenSourceKey && (activite.organisateur === tokenSourceKey || activite.commune === tokenSourceKey);
    metadata.verifie =
      ownedByToken || isAffiliated(email, [activite.contact_email, activite.lien_source]) ? "oui" : "non";
  } else {
    const organisme = typeof organismeRaw === "string" ? organismeRaw.trim() : "";
    if (!organisme || organisme.length > 200) {
      return jsonResponse(400, { error: "Merci d'indiquer le nom de votre organisme." });
    }
    productName = `Partenaire Trouvéo — ${organisme}`;
    metadata.organisme = organisme;
    // Toutes les activités connues de cet organisme (même logique que
    // groupKey() côté client : organisateur, sinon commune) - un seul
    // contact_email ou lien_source qui correspond suffit à vérifier.
    let refs = [];
    try {
      const res = await fetch(
        `${supabaseUrl}/rest/v1/activites?select=contact_email,lien_source&or=(organisateur.eq.${encodeURIComponent(organisme)},commune.eq.${encodeURIComponent(organisme)})&limit=200`,
        { headers: { apikey: secretKey, Authorization: `Bearer ${secretKey}` } }
      );
      const rows = await res.json();
      refs = Array.isArray(rows) ? rows.flatMap((r) => [r.contact_email, r.lien_source]) : [];
    } catch (err) {
      console.error("Vérification de l'organisme impossible", err);
      // Non bloquant : à défaut de vérifier, on marque juste "non vérifié"
      // plutôt que de refuser le paiement pour une panne transitoire.
    }
    metadata.verifie = tokenSourceKey === organisme || isAffiliated(email, refs) ? "oui" : "non";
  }

  const { montant_cents } = OFFRES[offre];

  const params = {
    mode: "payment",
    customer_email: email,
    "line_items[0][price_data][currency]": "eur",
    "line_items[0][price_data][unit_amount]": String(montant_cents),
    "line_items[0][price_data][product_data][name]": productName,
    "line_items[0][quantity]": "1",
    success_url: `${SITE_URL}/partenaires.html?paiement=succes&session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${SITE_URL}/partenaires.html?paiement=annule`,
  };
  for (const [key, value] of Object.entries(metadata)) {
    params[`metadata[${key}]`] = value;
  }

  try {
    const res = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${stripeKey}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: toFormUrlEncoded(params),
      signal: AbortSignal.timeout(10000),
    });
    const data = await res.json();
    if (!res.ok) {
      console.error("Erreur Stripe", res.status, data);
      return jsonResponse(502, { error: "Le paiement n'a pas pu être initié, réessayez dans un instant." });
    }
    return jsonResponse(200, { url: data.url });
  } catch (err) {
    console.error("Appel à Stripe impossible", err);
    return jsonResponse(502, { error: "Le paiement n'a pas pu être initié, réessayez dans un instant." });
  }
}

export async function onRequest() {
  return jsonResponse(405, { error: "Méthode non autorisée." });
}

// true si `email` correspond exactement à l'une des références connues
// (contact_email d'une soumission), OU si son domaine correspond au
// domaine d'un lien_source connu (ex. email @sportfunactiv.be pour une
// activité dont le lien source est sportfunactiv.be/...) - une
// correspondance sur une seule des références suffit.
function isAffiliated(email, references) {
  const emailLower = email.trim().toLowerCase();
  const emailDomain = domainOf(emailLower);
  for (const ref of references) {
    if (!ref) continue;
    if (ref.includes("@")) {
      if (ref.trim().toLowerCase() === emailLower) return true;
    } else if (emailDomain) {
      const refDomain = domainOf(ref);
      if (refDomain && refDomain === emailDomain) return true;
    }
  }
  return false;
}

function domainOf(value) {
  if (!value) return null;
  if (value.includes("@")) return value.split("@")[1].toLowerCase();
  try {
    return new URL(value).hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return null;
  }
}

function toFormUrlEncoded(params) {
  return Object.entries(params)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");
}

function jsonResponse(statusCode, body) {
  return new Response(JSON.stringify(body), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}
