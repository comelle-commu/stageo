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
// Corps de requête en multipart/form-data (pas JSON) : soumettre-activite.html
// permet de joindre un PDF/Word en plus des champs texte.
//
// PAS d'auto-publication : cette fonction écrit uniquement dans
// `soumissions_activites` (statut='en_attente' par défaut). Une soumission
// n'apparaît sur le vrai site qu'après relecture manuelle (statut passé à
// 'approuvee' dans le Table editor Supabase) ET reprise par
// scrapers/import_soumissions.py - voir ce fichier et
// docs/partenariats-premium-2026-08-31.md.
//
// Deux façons de soumettre : soit les champs détaillés (nom, type, dates)
// sont tous les trois remplis, soit un lien ou un document (PDF/Word,
// joint à la notification admin par email) permet à Muriel d'aller
// chercher les infos elle-même - dans ce cas les champs manquants sont
// remplacés par des valeurs "À déterminer" en attendant la relecture.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const VALID_TYPES = new Set(["Sport", "Art & créativité", "Sciences & nature", "Langues", "Multi-activités"]);
const MAX_FILE_BYTES = 8 * 1024 * 1024;
const ALLOWED_FILE_RE = /\.(pdf|docx?)$/i;

export async function onRequestPost(context) {
  const { request, env } = context;

  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secretKey) {
    console.error("SUPABASE_URL ou SUPABASE_SECRET_KEY manquant dans les variables d'environnement Cloudflare");
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }

  let form;
  try {
    form = await request.formData();
  } catch {
    return jsonResponse(400, { error: "Requête invalide." });
  }

  const str = (key) => {
    const v = form.get(key);
    return typeof v === "string" ? v.trim() : "";
  };

  const organisateur = str("organisateur");
  const contactEmail = str("contact_email");
  const nomActivite = str("nom_activite");
  const typeActivite = str("type_activite");
  const dates = str("dates");
  const commune = str("commune");
  const lieu = str("lieu");
  const prix = str("prix");
  const modalitesInscription = str("modalites_inscription");
  const lienSource = str("lien_source");
  const descriptionLongue = str("description_longue");

  const fichierRaw = form.get("fichier");
  const fichier = fichierRaw && typeof fichierRaw === "object" && fichierRaw.size > 0 ? fichierRaw : null;

  if (!organisateur || organisateur.length > 200) {
    return jsonResponse(400, { error: "Merci d'indiquer le nom de votre organisme." });
  }
  if (!EMAIL_RE.test(contactEmail)) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }
  if (typeActivite && !VALID_TYPES.has(typeActivite)) {
    return jsonResponse(400, { error: "Type d'activité invalide." });
  }
  if (fichier) {
    if (fichier.size > MAX_FILE_BYTES) {
      return jsonResponse(400, { error: "Le fichier dépasse 8 Mo - envoyez-le plutôt par email à hello@trouveo.be." });
    }
    if (!ALLOWED_FILE_RE.test(fichier.name || "")) {
      return jsonResponse(400, { error: "Format de fichier non pris en charge (PDF ou Word uniquement)." });
    }
  }

  // Soit les 3 champs détaillés sont remplis, soit un lien/document permet
  // d'aller chercher les infos manuellement - voir l'en-tête du fichier.
  const detailsComplets = nomActivite && typeActivite && dates;
  const raccourciFourni = lienSource || fichier;
  if (!detailsComplets && !raccourciFourni) {
    return jsonResponse(400, {
      error: "Merci de remplir le nom, le type et les dates de l'activité, ou de transmettre un lien/document à la place.",
    });
  }

  const ageMinRaw = form.get("age_min");
  const ageMaxRaw = form.get("age_max");
  const ageMin = ageMinRaw == null || ageMinRaw === "" ? null : Number(ageMinRaw);
  const ageMax = ageMaxRaw == null || ageMaxRaw === "" ? null : Number(ageMaxRaw);
  if (ageMin !== null && (Number.isNaN(ageMin) || ageMin < 0 || ageMin > 25)) {
    return jsonResponse(400, { error: "Âge minimum invalide." });
  }
  if (ageMax !== null && (Number.isNaN(ageMax) || ageMax < 0 || ageMax > 25)) {
    return jsonResponse(400, { error: "Âge maximum invalide." });
  }

  const viaRaccourci = !detailsComplets;
  const row = {
    organisateur,
    commune,
    nom_activite: nomActivite || "À déterminer (voir lien/document fourni)",
    type_activite: typeActivite || "Multi-activités",
    dates: dates || "À déterminer",
    age_min: ageMin,
    age_max: ageMax,
    prix,
    lieu,
    modalites_inscription: modalitesInscription,
    lien_source: lienSource,
    description_longue: descriptionLongue || null,
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
      context.waitUntil(sendConfirmationEmail(env, row, viaRaccourci).catch((err) => {
        console.error("Envoi de l'email de confirmation impossible", err);
      }));
      context.waitUntil(notifyAdminOfSubmission(env, row, fichier).catch((err) => {
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

// btoa() seul plante sur un gros fichier passé d'un coup à
// String.fromCharCode (dépassement de la pile d'appels) - encodage par
// petits blocs pour rester sûr jusqu'à MAX_FILE_BYTES.
async function fileToBase64(file) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  const chunkSize = 8192;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

async function sendConfirmationEmail(env, row, viaRaccourci) {
  const apiKey = env.BREVO_API_KEY;
  const senderEmail = env.BREVO_SENDER_EMAIL;
  if (!apiKey || !senderEmail) {
    console.error("BREVO_API_KEY ou BREVO_SENDER_EMAIL manquant - email de confirmation ignoré");
    return;
  }
  const senderName = env.BREVO_SENDER_NAME || "Trouvéo";

  const intro = viaRaccourci
    ? "Nous complétons les informations manquantes à partir de ce que vous nous avez transmis, puis nous relisons le tout avant publication."
    : "Nous la relisons avant de la publier (dates, âge, tarif, modalités).";

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
    ${intro} Vous recevrez un email dès qu'elle sera en ligne sur trouveo.be. Aucune inscription,
    aucun changement sans que vous en soyez informé·e.
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

async function notifyAdminOfSubmission(env, row, fichier) {
  const apiKey = env.BREVO_API_KEY;
  const senderEmail = env.BREVO_SENDER_EMAIL;
  const notifyEmail = env.ADMIN_NOTIFY_EMAIL;
  if (!apiKey || !senderEmail || !notifyEmail) return; // notification optionnelle, pas de config = pas d'envoi

  const senderName = env.BREVO_SENDER_NAME || "Trouvéo";
  const lienLine = row.lien_source ? `<p>Lien transmis : <a href="${esc(row.lien_source)}">${esc(row.lien_source)}</a></p>` : "";
  const fichierLine = fichier ? `<p>Document joint : ${esc(fichier.name)}</p>` : "";

  const payload = {
    sender: { name: senderName, email: senderEmail },
    to: [{ email: notifyEmail }],
    subject: "Trouvéo — nouvelle activité soumise à relire",
    htmlContent:
      `<p>Nouvelle activité soumise par <strong>${esc(row.organisateur)}</strong> (${esc(row.contact_email)}), en attente de relecture.</p>` +
      `<p><strong>${esc(row.nom_activite)}</strong><br>${esc(row.dates)} · ${esc(row.commune || "commune non précisée")}</p>` +
      lienLine + fichierLine +
      `<p>À relire et approuver (statut → 'approuvee') dans la table <code>soumissions_activites</code> sur Supabase.</p>`,
  };

  // Le document joint (si présent) part directement en pièce jointe de cet
  // email plutôt que d'être stocké quelque part - pas de bucket de fichiers
  // à gérer, Muriel l'a simplement dans sa boîte mail pour le relire.
  if (fichier) {
    payload.attachment = [{ name: fichier.name, content: await fileToBase64(fichier) }];
  }

  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": apiKey, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(15000),
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
