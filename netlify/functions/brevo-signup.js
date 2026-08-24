// Relais entre le formulaire de stageo-landing.html et l'API Brevo.
//
// Pourquoi ce relais existe : Brevo n'a pas de notion de clé "publique" /
// "restreinte" comme Stripe ou Supabase - une seule clé API, qui donne un
// accès complet au compte (lire/écrire tous les contacts, envoyer des
// emails, etc.). L'exposer dans le HTML/JS servi au navigateur la rendrait
// immédiatement récupérable par n'importe qui (view-source suffit). Cette
// fonction Netlify tourne côté serveur : la clé reste dans une variable
// d'environnement Netlify, jamais envoyée au navigateur.
//
// Variables d'environnement requises (Netlify → Site settings → Environment
// variables - voir docs/brevo-signup-2026-08-24.md pour le pas à pas) :
//   BREVO_API_KEY  - clé API Brevo (Settings → SMTP & API → API Keys)
//   BREVO_LIST_ID  - identifiant numérique de la liste "Stagéo - liste d'attente"

const BREVO_API_URL = "https://api.brevo.com/v3/contacts";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return jsonResponse(405, { error: "Méthode non autorisée." });
  }

  const apiKey = process.env.BREVO_API_KEY;
  const listId = process.env.BREVO_LIST_ID;
  if (!apiKey || !listId) {
    console.error("BREVO_API_KEY ou BREVO_LIST_ID manquant dans les variables d'environnement Netlify");
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }

  let email;
  try {
    ({ email } = JSON.parse(event.body || "{}"));
  } catch {
    return jsonResponse(400, { error: "Requête invalide." });
  }

  if (typeof email !== "string" || !EMAIL_RE.test(email)) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }

  try {
    const brevoRes = await fetch(BREVO_API_URL, {
      method: "POST",
      headers: {
        "api-key": apiKey,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        email,
        listIds: [Number(listId)],
        // updateEnabled: une personne qui s'inscrit deux fois (les deux
        // formulaires de la page, ou un rechargement) ne doit pas voir une
        // erreur - Brevo met juste à jour le contact existant.
        updateEnabled: true,
      }),
    });

    // 201 = contact créé, 204 = contact existant mis à jour (updateEnabled) - les deux sont un succès.
    if (brevoRes.status === 201 || brevoRes.status === 204) {
      return jsonResponse(200, { ok: true });
    }

    const details = await brevoRes.json().catch(() => ({}));
    console.error("Réponse Brevo inattendue", brevoRes.status, details);
    return jsonResponse(502, { error: "L'inscription a échoué, réessayez dans un instant." });
  } catch (err) {
    console.error("Appel à l'API Brevo impossible", err);
    return jsonResponse(502, { error: "L'inscription a échoué, réessayez dans un instant." });
  }
};

function jsonResponse(statusCode, body) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}
