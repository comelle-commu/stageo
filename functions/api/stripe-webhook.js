// Reçoit la confirmation de paiement Stripe et active automatiquement
// Boost (activites_boost) ou Partenaire (organismes_premium) - remplace
// l'activation manuelle (Table editor) une fois le paiement réellement
// encaissé. C'est LA seule fonction qui écrit ces deux tables suite à un
// paiement : create-checkout-session.js ne fait que créer la session,
// avant tout paiement.
//
// Vérification de signature manuelle (HMAC-SHA256 via Web Crypto) plutôt
// que le SDK stripe-node : ce dépôt n'a ni package.json ni étape de
// build (voir create-checkout-session.js) - schéma documenté par Stripe
// ("Stripe-Signature: t=...,v1=...", HMAC-SHA256 de "{t}.{payload}").
//
// Variables d'environnement requises (Cloudflare Pages → Settings →
// Environment variables) :
//   STRIPE_WEBHOOK_SECRET - Dashboard Stripe → Developers → Webhooks →
//     endpoint https://trouveo.be/api/stripe-webhook, événement
//     "checkout.session.completed" → "Signing secret"
//   SUPABASE_URL / SUPABASE_SECRET_KEY - pour écrire activites_boost /
//     organismes_premium
//   BREVO_API_KEY / BREVO_SENDER_EMAIL / ADMIN_NOTIFY_EMAIL (optionnel) -
//     pour te prévenir par email à chaque vente (même mécanisme que
//     soumettre-activite.js)
//
// Route : fichier functions/api/stripe-webhook.js -> disponible sur
// /api/stripe-webhook - à configurer comme URL d'endpoint côté Stripe.

const TOLERANCE_SECONDS = 5 * 60; // rejette un webhook rejoué plus de 5 min après sa création

export async function onRequestPost(context) {
  const { request, env } = context;

  const webhookSecret = env.STRIPE_WEBHOOK_SECRET;
  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!webhookSecret || !supabaseUrl || !secretKey) {
    console.error("STRIPE_WEBHOOK_SECRET, SUPABASE_URL ou SUPABASE_SECRET_KEY manquant dans les variables d'environnement Cloudflare");
    // 500 plutôt que d'accuser réception : Stripe réessaiera une fois la
    // config corrigée, un événement de paiement ne doit jamais être perdu
    // silencieusement.
    return new Response("Configuration serveur incomplète.", { status: 500 });
  }

  const signatureHeader = request.headers.get("Stripe-Signature") || "";
  const rawBody = await request.text();

  const valid = await verifyStripeSignature(rawBody, signatureHeader, webhookSecret);
  if (!valid) {
    console.error("Signature Stripe invalide");
    return new Response("Signature invalide.", { status: 400 });
  }

  let event;
  try {
    event = JSON.parse(rawBody);
  } catch {
    return new Response("Payload JSON invalide.", { status: 400 });
  }

  if (event.type !== "checkout.session.completed") {
    // Accusé de réception normal pour tout événement qu'on ne traite pas
    // (compte activé, etc.) - Stripe envoie tous les événements souscrits
    // sur l'endpoint, pas seulement celui-ci si le dashboard en ajoute
    // d'autres un jour.
    return new Response("ok", { status: 200 });
  }

  const session = event.data && event.data.object;
  if (!session || session.payment_status !== "paid") {
    return new Response("ok", { status: 200 }); // paiement pas (encore) confirmé, rien à activer
  }

  const metadata = session.metadata || {};
  const offre = metadata.offre;
  const email = metadata.email || (session.customer_details && session.customer_details.email) || null;

  try {
    if (offre === "boost") {
      await activateBoost(supabaseUrl, secretKey, metadata.activite_id);
    } else if (offre === "partenaire") {
      await activatePartenaire(supabaseUrl, secretKey, metadata.organisme);
    } else {
      console.error("Webhook Stripe sans offre reconnue dans metadata", metadata);
      return new Response("ok", { status: 200 }); // accusé quand même - rejouer ne changerait rien sans metadata valide
    }
  } catch (err) {
    console.error("Activation après paiement impossible", err);
    // 500 : Stripe réessaiera - un paiement encaissé DOIT finir par
    // activer quelque chose, une erreur Supabase transitoire ne doit pas
    // laisser un client payant sans rien.
    return new Response("Activation impossible, nouvelle tentative attendue.", { status: 500 });
  }

  context.waitUntil(
    notifyAdminOfPayment(env, offre, metadata, session).catch((err) => {
      console.error("Notification de paiement impossible", err);
    })
  );

  return new Response("ok", { status: 200 });
}

export async function onRequest() {
  return new Response("Méthode non autorisée.", { status: 405 });
}

async function activateBoost(supabaseUrl, secretKey, activiteIdRaw) {
  const activiteId = Number(activiteIdRaw);
  if (!Number.isInteger(activiteId) || activiteId <= 0) {
    throw new Error(`activite_id invalide dans les metadata Stripe : ${activiteIdRaw}`);
  }
  const today = new Date();
  const jusquau = new Date(today.getTime() + 28 * 24 * 60 * 60 * 1000);
  const res = await fetch(`${supabaseUrl}/rest/v1/activites_boost?on_conflict=activite_id`, {
    method: "POST",
    headers: {
      apikey: secretKey,
      Authorization: `Bearer ${secretKey}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify([
      {
        activite_id: activiteId,
        boost_debute_le: isoDate(today),
        boost_jusquau: isoDate(jusquau),
      },
    ]),
  });
  if (!res.ok) {
    const details = await res.text().catch(() => "");
    throw new Error(`Supabase activites_boost ${res.status}: ${details}`);
  }
}

async function activatePartenaire(supabaseUrl, secretKey, organismeRaw) {
  const organisme = typeof organismeRaw === "string" ? organismeRaw.trim() : "";
  if (!organisme) {
    throw new Error("organisme manquant dans les metadata Stripe");
  }
  const today = new Date();
  const jusquau = new Date(today.getTime() + 365 * 24 * 60 * 60 * 1000);
  const res = await fetch(`${supabaseUrl}/rest/v1/organismes_premium?on_conflict=source_key`, {
    method: "POST",
    headers: {
      apikey: secretKey,
      Authorization: `Bearer ${secretKey}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify([
      {
        source_key: organisme,
        mis_en_avant_jusquau: isoDate(jusquau),
        mise_en_avant_complete: true,
        updated_at: today.toISOString(),
      },
    ]),
  });
  if (!res.ok) {
    const details = await res.text().catch(() => "");
    throw new Error(`Supabase organismes_premium ${res.status}: ${details}`);
  }
}

async function notifyAdminOfPayment(env, offre, metadata, session) {
  const apiKey = env.BREVO_API_KEY;
  const senderEmail = env.BREVO_SENDER_EMAIL;
  const notifyEmail = env.ADMIN_NOTIFY_EMAIL;
  if (!apiKey || !senderEmail || !notifyEmail) return; // notification optionnelle, pas de config = pas d'envoi

  const senderName = env.BREVO_SENDER_NAME || "Trouvéo";
  const montant = ((session.amount_total || 0) / 100).toFixed(2);
  const cible = offre === "boost" ? `Activité #${metadata.activite_id}` : `Organisme "${metadata.organisme}"`;
  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": apiKey, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      sender: { name: senderName, email: senderEmail },
      to: [{ email: notifyEmail }],
      subject: `Trouvéo — paiement ${offre === "boost" ? "Boost" : "Partenaire"} reçu (${montant}€)`,
      htmlContent:
        `<p>Paiement confirmé et activé automatiquement.</p>` +
        `<p><strong>${esc(cible)}</strong><br>${montant}€ · ${esc(metadata.email || "email inconnu")}</p>` +
        `<p>Rien à faire de ton côté - c'est déjà actif sur le site.</p>`,
    }),
    signal: AbortSignal.timeout(8000),
  });
  if (!resp.ok) {
    const details = await resp.text().catch(() => "");
    throw new Error(`Brevo ${resp.status}: ${details}`);
  }
}

function esc(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

// --- Vérification de signature Stripe (Web Crypto, sans SDK) --------------
//
// Schéma documenté : https://docs.stripe.com/webhooks#verify-manually
// En-tête "Stripe-Signature: t=<timestamp>,v1=<signature>[,v0=...]" -
// signature = HMAC-SHA256(secret, "{t}.{corps brut}"), encodée en hex.
// v0 est un ancien schéma (SHA1) ignoré ici, comme recommandé par Stripe.
async function verifyStripeSignature(rawBody, signatureHeader, secret) {
  const parts = Object.fromEntries(
    signatureHeader.split(",").map((p) => {
      const [k, v] = p.split("=");
      return [k, v];
    })
  );
  const timestamp = parts.t;
  const v1 = parts.v1;
  if (!timestamp || !v1) return false;

  const nowSeconds = Math.floor(Date.now() / 1000);
  if (Math.abs(nowSeconds - Number(timestamp)) > TOLERANCE_SECONDS) return false;

  const signedPayload = `${timestamp}.${rawBody}`;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signatureBytes = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(signedPayload));
  const expectedHex = bytesToHex(new Uint8Array(signatureBytes));

  return timingSafeEqual(expectedHex, v1);
}

function bytesToHex(bytes) {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}
