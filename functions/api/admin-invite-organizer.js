// Génère (ou régénère) le jeton d'accès "espace organisateur" d'un
// organisme déjà connu dans `organisateurs_contact`, et lui envoie le
// lien par email - voir supabase/migrations/20260902b_add_organizer_access_token.sql
// et functions/api/organisateur-espace.js.
//
// Suppose que la ligne organisateurs_contact (source_key, contact_email)
// existe déjà - alimentée automatiquement par une soumission
// (soumettre-activite.html) ou ajoutée à la main (Table editor Supabase),
// exactement comme pour les relances organisateurs déjà en place.
//
// Protégé par le même jeton partagé que admin-stats.js/boost-report.js
// (ADMIN_TOKEN, comparée à ?key=...) - pas un vrai système de comptes,
// juste vous qui déclenchez l'envoi. Ne jamais partager ce lien.
//
// Variables d'environnement requises :
//   SUPABASE_URL, SUPABASE_SECRET_KEY, ADMIN_TOKEN - comme admin-stats.js
//   BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME (optionnel)
//
// Route : /api/admin-invite-organizer?key=VOTRE_JETON&source_key=Ans

const SITE_URL = "https://trouveo.be";

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  if (!env.ADMIN_TOKEN || url.searchParams.get("key") !== env.ADMIN_TOKEN) {
    return new Response("Accès refusé.", { status: 403, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secretKey) {
    return new Response("Configuration serveur incomplète.", { status: 500 });
  }

  const sourceKey = url.searchParams.get("source_key");
  if (!sourceKey) {
    return new Response("Paramètre source_key manquant.", { status: 400 });
  }

  const headers = { apikey: secretKey, Authorization: `Bearer ${secretKey}` };
  const res = await fetch(
    `${supabaseUrl}/rest/v1/organisateurs_contact?select=source_key,contact_email,access_token&source_key=eq.${encodeURIComponent(sourceKey)}`,
    { headers }
  );
  const rows = await res.json();
  const contact = Array.isArray(rows) ? rows[0] : null;
  if (!contact) {
    return new Response(
      `Aucun contact connu pour "${sourceKey}" - ajoutez d'abord une ligne dans organisateurs_contact (Table editor) avant d'inviter.`,
      { status: 404 }
    );
  }

  const token = contact.access_token || generateToken();
  if (!contact.access_token) {
    const upd = await fetch(
      `${supabaseUrl}/rest/v1/organisateurs_contact?source_key=eq.${encodeURIComponent(sourceKey)}`,
      {
        method: "PATCH",
        headers: { ...headers, "Content-Type": "application/json", Prefer: "return=minimal" },
        body: JSON.stringify({ access_token: token }),
      }
    );
    if (!upd.ok) {
      const details = await upd.text().catch(() => "");
      return new Response(`Échec de l'enregistrement du jeton : ${details}`, { status: 502 });
    }
  }

  const lien = `${SITE_URL}/organisateur.html?token=${token}`;

  let emailStatus = "email non envoyé (BREVO_API_KEY/BREVO_SENDER_EMAIL manquant)";
  if (env.BREVO_API_KEY && env.BREVO_SENDER_EMAIL) {
    try {
      await sendInviteEmail(env, contact.contact_email, sourceKey, lien);
      emailStatus = `email envoyé à ${contact.contact_email}`;
    } catch (err) {
      emailStatus = `échec d'envoi de l'email : ${err.message}`;
    }
  }

  return new Response(`Lien : ${lien}\n${emailStatus}`, {
    status: 200,
    headers: { "Content-Type": "text/plain; charset=UTF-8" },
  });
}

function generateToken() {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function sendInviteEmail(env, contactEmail, sourceKey, lien) {
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

  <tr><td style="padding-bottom:24px;">
    <span style="font-family:'Grandstander',Arial,sans-serif;font-weight:700;font-size:21px;color:#015380;line-height:1.3;">
      Vos activités sont déjà sur Trouvéo
    </span>
  </td></tr>

  <tr><td style="padding-bottom:26px;color:#5C7A8C;font-size:14.5px;line-height:1.6;">
    Trouvéo est une plateforme qui recense les stages et activités pour enfants en Belgique francophone - nous avons repéré vos activités (${esc(sourceKey)})
    et les avons ajoutées à notre catalogue. Le lien ci-dessous vous donne accès à un espace pour les consulter, signaler une correction si besoin,
    et éventuellement les mettre en avant.
  </td></tr>

  <tr><td align="center" style="padding:0 0 22px;">
    <a href="${lien}" style="display:inline-block;background:#0197AF;color:#ffffff;text-decoration:none;
      font-family:'Work Sans',Arial,sans-serif;font-weight:700;font-size:14px;padding:14px 28px;border-radius:100px;">
      Accéder à mon espace →
    </a>
  </td></tr>

  <tr><td style="border-top:1px solid rgba(1,83,128,0.12);padding-top:18px;">
    <p style="color:#93A9B5;font-size:12px;line-height:1.6;margin:0;text-align:center;">
      Ce lien est personnel, gardez-le pour vous. Une question ? Écrivez à hello@trouveo.be.
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
      subject: "Vos activités sont déjà sur Trouvéo",
      htmlContent: html,
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

export async function onRequest() {
  return new Response("Méthode non autorisée.", { status: 405 });
}
