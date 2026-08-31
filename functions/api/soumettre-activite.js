// Relais entre le formulaire de soumettre-activite.html ("soumettez votre
// activité vous-même") et la table Supabase `soumissions_activites`.
//
// Même raison d'être qu'un relais serveur que les autres fonctions de ce
// dossier : la clé secrète Supabase ne doit jamais être envoyée au
// navigateur.
//
// Variables d'environnement requises (Cloudflare Pages → Settings →
// Environment variables) - toutes déjà utilisées par save-criteria.js :
//   SUPABASE_URL          - même valeur que dans scrapers/.env
//   SUPABASE_SECRET_KEY    - idem
//   BREVO_API_KEY          - idem
//   BREVO_SENDER_EMAIL     - idem
//   BREVO_SENDER_NAME      - optionnel, "Trouvéo" par défaut
//   ADMIN_NOTIFY_EMAIL     - optionnel (voir brevo-signup.js) - si définie,
//                            Muriel reçoit un email à chaque nouvelle
//                            soumission, pour aller la relire dans Supabase
//
// Route : fichier functions/api/soumettre-activite.js -> disponible sur
// /api/soumettre-activite
//
// PAS d'auto-publication : cette fonction écrit uniquement dans
// `soumissions_activites` (statut='en_attente' par défaut). Une soumission
// n'apparaît sur le vrai site qu'après relecture manuelle (statut passé à
// 'approuvee' dans le Table editor Supabase) ET reprise par
// scrapers/import_soumissions.py - voir ce fichier et
// docs/partenariats-premium-2026-08-31.md.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const VALID_TYPES = new Set(["Sport", "Art & créativité", "Sciences & nature", "Langues", "Multi-activités"]);

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

  const {
    organisateur, commune, nom_activite: nomActivite, type_activite: typeActivite,
    dates, age_min: ageMinRaw, age_max: ageMaxRaw, prix, lieu,
    modalites_inscription: modalitesInscription, lien_source: lienSource,
    description_longue: descriptionLongue, contact_email: contactEmail,
  } = body || {};

  if (typeof contactEmail !== "string" || !EMAIL_RE.test(contactEmail)) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }
  if (typeof organisateur !== "string" || !organisateur.trim() || organisateur.trim().length > 200) {
    return jsonResponse(400, { error: "Merci d'indiquer le nom de votre organisme." });
  }
  if (typeof nomActivite !== "string" || !nomActivite.trim() || nomActivite.trim().length > 200) {
    return jsonResponse(400, { error: "Merci d'indiquer le nom de l'activité." });
  }
  if (typeof typeActivite !== "string" || !VALID_TYPES.has(typeActivite)) {
    return jsonResponse(400, { error: "Type d'activité invalide." });
  }
  if (typeof dates !== "string" || !dates.trim() || dates.trim().length > 200) {
    return jsonResponse(400, { error: "Merci d'indiquer les dates de l'activité." });
  }
  const ageMin = ageMinRaw === "" || ageMinRaw == null ? null : Number(ageMinRaw);
  const ageMax = ageMaxRaw === "" || ageMaxRaw == null ? null : Number(ageMaxRaw);
  if (ageMin !== null && (Number.isNaN(ageMin) || ageMin < 0 || ageMin > 25)) {
    return jsonResponse(400, { error: "Âge minimum invalide." });
  }
  if (ageMax !== null && (Number.isNaN(ageMax) || ageMax < 0 || ageMax > 25)) {
    return jsonResponse(400, { error: "Âge maximum invalide." });
  }

  const row = {
    organisateur: organisateur.trim(),
    commune: typeof commune === "string" ? commune.trim() : "",
    nom_activite: nomActivite.trim(),
    type_activite: typeActivite,
    dates: dates.trim(),
    age_min: ageMin,
    age_max: ageMax,
    prix: typeof prix === "string" ? prix.trim() : "",
    lieu: typeof lieu === "string" ? lieu.trim() : "",
    modalites_inscription: typeof modalitesInscription === "string" ? modalitesInscription.trim() : "",
    lien_source: typeof lienSource === "string" ? lienSource.trim() : "",
    description_longue: typeof descriptionLongue === "string" && descriptionLongue.trim() ? descriptionLongue.trim() : null,
    contact_email: contactEmail,
  };

  try {
    const res = await fetch(`${supabaseUrl}/rest/v1/soumissions_activites`, {
      method: "POST",
      headers: {
        apikey: secretKey,
        Authorization: `Bearer ${secretKey}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify([row]),
    });

    if (res.status === 201 || res.status === 200) {
      context.waitUntil(sendConfirmationEmail(env, row).catch((err) => {
        console.error("Envoi de l'email de confirmation impossible", err);
      }));
      context.waitUntil(notifyAdminOfSubmission(env, row).catch((err) => {
        console.error("Notification de nouvelle soumission impossible", err);
      }));
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

function esc(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function sendConfirmationEmail(env, row) {
  const apiKey = env.BREVO_API_KEY;
  const senderEmail = env.BREVO_SENDER_EMAIL;
  if (!apiKey || !senderEmail) {
    console.error("BREVO_API_KEY ou BREVO_SENDER_EMAIL manquant - email de confirmation ignoré");
    return;
  }
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
      Votre activité a bien été reçue
    </span>
  </td></tr>

  <tr><td style="padding-bottom:18px;color:#5C7A8C;font-size:14.5px;line-height:1.6;">
    Nous la relisons avant de la publier (dates, âge, tarif, modalités) - vous recevrez
    un email dès qu'elle sera en ligne sur trouveo.be. Aucune inscription, aucun changement
    sans que vous en soyez informé·e.
  </td></tr>

  <tr><td style="padding:14px 16px;background:#FFFFFF;border:1px solid rgba(1,83,128,0.12);border-radius:14px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:0 0 8px;color:#93A9B5;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">Activité</td></tr>
      <tr><td style="padding:0 0 14px;color:#015380;font-size:14.5px;">${esc(row.nom_activite)}</td></tr>
      <tr><td style="padding:0 0 8px;color:#93A9B5;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">Dates</td></tr>
      <tr><td style="padding:0;color:#015380;font-size:14.5px;">${esc(row.dates)}</td></tr>
    </table>
  </td></tr>

  <tr><td style="border-top:1px solid rgba(1,83,128,0.12);padding-top:18px;margin-top:14px;">
    <p style="color:#93A9B5;font-size:12px;line-height:1.6;margin:0;text-align:center;">
      Une erreur dans ces informations ? Répondez simplement à cet email, ou écrivez-nous à hello@trouveo.be.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>`;

  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": apiKey, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      sender: { name: senderName, email: senderEmail },
      to: [{ email: row.contact_email }],
      subject: "Votre activité a bien été reçue",
      htmlContent: html,
    }),
    signal: AbortSignal.timeout(8000),
  });
  if (!resp.ok) {
    const details = await resp.text().catch(() => "");
    throw new Error(`Brevo ${resp.status}: ${details}`);
  }
}

async function notifyAdminOfSubmission(env, row) {
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
      subject: "Trouvéo — nouvelle activité soumise à relire",
      htmlContent:
        `<p>Nouvelle activité soumise par <strong>${esc(row.organisateur)}</strong> (${esc(row.contact_email)}), en attente de relecture.</p>` +
        `<p><strong>${esc(row.nom_activite)}</strong><br>${esc(row.dates)} · ${esc(row.commune || "commune non précisée")}</p>` +
        `<p>À relire et approuver (statut → 'approuvee') dans la table <code>soumissions_activites</code> sur Supabase.</p>`,
    }),
    signal: AbortSignal.timeout(8000),
  });
  if (!resp.ok) {
    const details = await resp.text().catch(() => "");
    throw new Error(`Brevo ${resp.status}: ${details}`);
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
