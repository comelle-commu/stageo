// Reçoit une demande de correction depuis l'espace organisateur
// (organisateur.html) et te la transmet par email - PAS d'écriture
// directe dans `activites` : ces lignes sont réécrites chaque semaine
// par le ratissage automatique (voir scrapers/run_all.py), donc une
// correction manuelle non protégée serait silencieusement écrasée au
// prochain passage. Passe par une relecture, comme les soumissions
// d'activités (soumettre-activite.html) déjà en place.
//
// Variables d'environnement requises : SUPABASE_URL, SUPABASE_SECRET_KEY,
//   BREVO_API_KEY, BREVO_SENDER_EMAIL, ADMIN_NOTIFY_EMAIL
//
// Route : /api/organisateur-signaler-correction (POST)

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
  const { token, activite_id: activiteIdRaw, message } = body || {};

  if (typeof token !== "string" || !token) {
    return jsonResponse(400, { error: "Lien invalide." });
  }
  const activiteId = Number(activiteIdRaw);
  if (!Number.isInteger(activiteId) || activiteId <= 0) {
    return jsonResponse(400, { error: "Activité invalide." });
  }
  const texte = typeof message === "string" ? message.trim().slice(0, 2000) : "";
  if (!texte) {
    return jsonResponse(400, { error: "Merci de décrire la correction souhaitée." });
  }

  const headers = { apikey: secretKey, Authorization: `Bearer ${secretKey}` };

  const contactRes = await fetch(
    `${supabaseUrl}/rest/v1/organisateurs_contact?select=source_key,contact_email&access_token=eq.${encodeURIComponent(token)}`,
    { headers }
  );
  const contactRows = await contactRes.json();
  const contact = Array.isArray(contactRows) ? contactRows[0] : null;
  if (!contact) {
    return jsonResponse(404, { error: "Lien invalide ou expiré." });
  }

  const activiteRes = await fetch(
    `${supabaseUrl}/rest/v1/activites?select=id,nom_activite,organisateur,commune&id=eq.${activiteId}`,
    { headers }
  );
  const activiteRows = await activiteRes.json();
  const activite = Array.isArray(activiteRows) ? activiteRows[0] : null;
  // Vérifie que l'activité appartient bien à CET organisme (via le
  // jeton) - sans ça, le jeton d'un organisme donnerait le droit de
  // signaler une correction sur l'activité de n'importe qui d'autre.
  const belongsToOrganizer =
    activite && (activite.organisateur === contact.source_key || activite.commune === contact.source_key);
  if (!belongsToOrganizer) {
    return jsonResponse(404, { error: "Cette activité ne correspond pas à votre espace." });
  }

  const apiKey = env.BREVO_API_KEY;
  const senderEmail = env.BREVO_SENDER_EMAIL;
  const notifyEmail = env.ADMIN_NOTIFY_EMAIL;
  if (apiKey && senderEmail && notifyEmail) {
    try {
      await notifyAdmin(env, contact, activite, texte);
    } catch (err) {
      console.error("Notification de correction impossible", err);
      return jsonResponse(502, { error: "L'envoi a échoué, réessayez dans un instant." });
    }
  } else {
    console.error("BREVO_API_KEY/BREVO_SENDER_EMAIL/ADMIN_NOTIFY_EMAIL manquant - correction non transmise", {
      source_key: contact.source_key,
      activite_id: activiteId,
    });
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }

  return jsonResponse(200, { ok: true });
}

export async function onRequest() {
  return jsonResponse(405, { error: "Méthode non autorisée." });
}

async function notifyAdmin(env, contact, activite, texte) {
  const senderName = env.BREVO_SENDER_NAME || "Trouvéo";
  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": env.BREVO_API_KEY, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      sender: { name: senderName, email: env.BREVO_SENDER_EMAIL },
      to: [{ email: env.ADMIN_NOTIFY_EMAIL }],
      subject: `Trouvéo — correction demandée par ${contact.source_key}`,
      htmlContent:
        `<p>Correction demandée par <strong>${esc(contact.source_key)}</strong> (${esc(contact.contact_email)}) ` +
        `via son espace organisateur.</p>` +
        `<p><strong>Activité :</strong> ${esc(activite.nom_activite)} (id ${activite.id})</p>` +
        `<p><strong>Message :</strong><br>${esc(texte).replace(/\n/g, "<br>")}</p>` +
        `<p>À corriger à la main dans Supabase si légitime - ce champ n'est jamais écrasé sans relecture.</p>`,
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

function jsonResponse(statusCode, body) {
  return new Response(JSON.stringify(body), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}
