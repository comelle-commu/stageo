// Relais entre le formulaire de index.html (landing page Trouvéo) et l'API Brevo.
// Version Cloudflare Pages Functions - portée depuis netlify/functions/brevo-signup.js
// suite au blocage du plan gratuit Netlify (limite de build atteinte, reset dans
// 3 semaines) - migration vers Cloudflare Pages (limites gratuites bien plus
// généreuses, aucune raison d'y retomber pour un site en bêta).
//
// Pourquoi ce relais existe : Brevo n'a pas de notion de clé "publique" /
// "restreinte" comme Stripe ou Supabase - une seule clé API, qui donne un
// accès complet au compte. L'exposer dans le HTML/JS servi au navigateur la
// rendrait immédiatement récupérable par n'importe qui (view-source suffit).
// Cette fonction tourne côté serveur : la clé reste dans une variable
// d'environnement Cloudflare, jamais envoyée au navigateur.
//
// Variables d'environnement requises (Cloudflare Pages → Settings →
// Environment variables) :
//   BREVO_API_KEY     - clé API Brevo (Settings → SMTP & API → API Keys)
//   BREVO_LIST_ID     - identifiant numérique de la liste "Stagéo - liste d'attente"
//   BREVO_SENDER_EMAIL - expéditeur des emails transactionnels (même valeur que
//                         save-criteria.js) - sert ici à notifier une nouvelle inscription
//   BREVO_SENDER_NAME  - optionnel, "Trouvéo" par défaut
//   ADMIN_NOTIFY_EMAIL - optionnel, adresse à prévenir à chaque nouvelle inscription
//                         (si absent, la notification est simplement ignorée - ne bloque
//                         jamais l'inscription elle-même)
//
// Route : fichier functions/api/brevo-signup.js -> disponible sur /api/brevo-signup
// (convention de routage par chemin de fichier de Cloudflare Pages Functions).

const BREVO_API_URL = "https://api.brevo.com/v3/contacts";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function onRequestPost(context) {
  const { request, env } = context;

  const apiKey = env.BREVO_API_KEY;
  const listId = env.BREVO_LIST_ID;
  if (!apiKey || !listId) {
    console.error("BREVO_API_KEY ou BREVO_LIST_ID manquant dans les variables d'environnement Cloudflare");
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }

  let email;
  try {
    ({ email } = await request.json());
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
      // Notification seulement pour une VRAIE nouvelle inscription (201) - pas à
      // chaque rechargement de page/resoumission d'un email déjà connu (204),
      // sinon la notification perd tout son sens. Best-effort : un souci d'envoi
      // ne doit jamais faire échouer l'inscription elle-même.
      if (brevoRes.status === 201) {
        context.waitUntil(notifyAdminOfSignup(env, email).catch((err) => {
          console.error("Notification de nouvelle inscription impossible", err);
        }));
      }
      return jsonResponse(200, { ok: true });
    }

    const details = await brevoRes.json().catch(() => ({}));
    console.error("Réponse Brevo inattendue", brevoRes.status, details);
    return jsonResponse(502, { error: "L'inscription a échoué, réessayez dans un instant." });
  } catch (err) {
    console.error("Appel à l'API Brevo impossible", err);
    return jsonResponse(502, { error: "L'inscription a échoué, réessayez dans un instant." });
  }
}

async function notifyAdminOfSignup(env, email) {
  const apiKey = env.BREVO_API_KEY;
  const senderEmail = env.BREVO_SENDER_EMAIL;
  const notifyEmail = env.ADMIN_NOTIFY_EMAIL;
  if (!apiKey || !senderEmail || !notifyEmail) return; // notification optionnelle, pas de config = pas d'envoi

  const senderName = env.BREVO_SENDER_NAME || "Trouvéo";
  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": apiKey, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      sender: { name: senderName, email: senderEmail },
      to: [{ email: notifyEmail }],
      subject: "Trouvéo — nouvelle inscription",
      htmlContent: `<p>Nouvelle inscription à la liste d'attente : <strong>${email.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</strong></p>`,
    }),
    signal: AbortSignal.timeout(8000),
  });
  if (!resp.ok) {
    const details = await resp.text().catch(() => "");
    throw new Error(`Brevo ${resp.status}: ${details}`);
  }
}

// Cloudflare appelle onRequestPost pour POST ; toute autre méthode (GET,
// PUT...) tombe ici -> 405, comme côté Netlify.
export async function onRequest() {
  return jsonResponse(405, { error: "Méthode non autorisée." });
}

function jsonResponse(statusCode, body) {
  return new Response(JSON.stringify(body), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}
