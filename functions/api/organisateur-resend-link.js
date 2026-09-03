// "Vous avez perdu votre lien ?" (partenaires.html) - renvoie le lien
// d'accès à l'espace organisateur d'un contact déjà connu, sur simple
// email. Toujours la même réponse générique que l'email corresponde ou
// non à un contact connu (voir jsonResponse plus bas) - comme un "mot de
// passe oublié" classique, pour ne jamais confirmer/infirmer qu'une
// adresse donnée est déjà enregistrée.
//
// Variables d'environnement requises : SUPABASE_URL, SUPABASE_SECRET_KEY,
//   BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME (optionnel)
//
// Route : /api/organisateur-resend-link (POST)

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SITE_URL = "https://trouveo.be";
const GENERIC_MESSAGE =
  "Si cette adresse correspond à un organisme déjà connu, vous allez recevoir un nouveau lien d'ici quelques minutes.";

export async function onRequestPost(context) {
  const { request, env } = context;

  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secretKey) {
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(400, { error: "Requête invalide." });
  }
  const { email } = body || {};
  if (typeof email !== "string" || !EMAIL_RE.test(email)) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }
  const emailNorm = email.trim().toLowerCase();

  try {
    const res = await fetch(
      `${supabaseUrl}/rest/v1/organisateurs_contact?select=source_key,contact_email,access_token&contact_email=ilike.${encodeURIComponent(emailNorm)}`,
      { headers: { apikey: secretKey, Authorization: `Bearer ${secretKey}` } }
    );
    const rows = await res.json();
    const contact = Array.isArray(rows) ? rows[0] : null;

    if (contact) {
      let token = contact.access_token;
      if (!token) {
        token = generateToken();
        await fetch(`${supabaseUrl}/rest/v1/organisateurs_contact?source_key=eq.${encodeURIComponent(contact.source_key)}`, {
          method: "PATCH",
          headers: {
            apikey: secretKey,
            Authorization: `Bearer ${secretKey}`,
            "Content-Type": "application/json",
            Prefer: "return=minimal",
          },
          body: JSON.stringify({ access_token: token }),
        });
      }
      if (env.BREVO_API_KEY && env.BREVO_SENDER_EMAIL) {
        await sendLinkEmail(env, contact.contact_email, `${SITE_URL}/organisateur.html?token=${token}`).catch((err) => {
          console.error("Envoi du lien impossible", err);
        });
      }
    }
  } catch (err) {
    console.error("Recherche du contact impossible", err);
    // Toujours la même réponse générique, même en cas d'erreur interne -
    // ne jamais révéler côté client si quelque chose a spécifiquement
    // échoué pour cet email.
  }

  return jsonResponse(200, { ok: true, message: GENERIC_MESSAGE });
}

export async function onRequest() {
  return jsonResponse(405, { error: "Méthode non autorisée." });
}

async function sendLinkEmail(env, contactEmail, lien) {
  const senderName = env.BREVO_SENDER_NAME || "Trouvéo";
  const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Grandstander:wght@700;800&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;background:#FFFDF8;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFFDF8;">
<tr><td align="center" style="padding:36px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;font-family:'Work Sans',Arial,sans-serif;">
  <tr><td style="padding-bottom:22px;">
    <span style="font-family:'Grandstander',Arial,sans-serif;font-weight:800;font-size:22px;color:#015380;">Trouvéo</span>
  </td></tr>
  <tr><td style="padding-bottom:18px;color:#5C7A8C;font-size:14.5px;line-height:1.6;">
    Voici votre lien vers votre espace organisateur, comme demandé.
  </td></tr>
  <tr><td align="center" style="padding:6px 0 24px;">
    <a href="${lien}" style="display:inline-block;background:#0197AF;color:#ffffff;text-decoration:none;
      font-family:'Work Sans',Arial,sans-serif;font-weight:700;font-size:14px;padding:14px 28px;border-radius:100px;">
      Voir mes activités →
    </a>
  </td></tr>
  <tr><td style="border-top:1px solid rgba(1,83,128,0.12);padding-top:18px;">
    <p style="color:#93A9B5;font-size:12px;line-height:1.6;margin:0;text-align:center;">
      Ce lien est personnel, gardez-le pour vous. Une question ? Répondez simplement à cet email.
    </p>
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>`;

  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": env.BREVO_API_KEY, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      sender: { name: senderName, email: env.BREVO_SENDER_EMAIL },
      to: [{ email: contactEmail }],
      subject: "Votre lien vers votre espace organisateur Trouvéo",
      htmlContent: html,
    }),
    signal: AbortSignal.timeout(8000),
  });
  if (!resp.ok) {
    const details = await resp.text().catch(() => "");
    throw new Error(`Brevo ${resp.status}: ${details}`);
  }
}

function generateToken() {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function jsonResponse(statusCode, body) {
  return new Response(JSON.stringify(body), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}
