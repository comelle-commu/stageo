// Vérifie qu'une personne est bien affiliée à un organisme et lui donne
// accès à l'espace organisateur (jeton) si oui - deux points d'entrée
// possibles, mêmes règles de vérification pour les deux :
//   - depuis une carte de activites.html ("C'est votre activité ?") :
//     {activite_id, email} - l'organisme se déduit de cette activité précise.
//   - depuis partenaires.html ("Accéder à mon espace") : {organisme, email}
//     - la personne tape elle-même le nom de son organisme (plus simple
//     qu'une recherche par nom d'activité, qui échoue si le libellé exact
//     scrapé diffère de ce qu'elle devine, ex. "CCJV" vs "centre communal
//     des jeux de vacances").
//
// Vérification : même logique que metadata.verifie dans
// create-checkout-session.js - l'email doit correspondre au contact déjà
// connu pour cet organisme (organisateurs_contact) OU au domaine du site
// source (lien_source) d'une de ses activités. Si ça correspond : jeton
// généré (ou réutilisé s'il existe déjà) et renvoyé directement, la
// personne atterrit dans organisateur.html sans attendre un email - elle
// choisit ensuite elle-même quoi booster/mettre en avant depuis sa propre
// liste, jamais en payant à l'aveugle pour une activité devinée. Si ça ne
// correspond pas : accès refusé, mais pas silencieusement - une
// notification part immédiatement pour que Muriel vérifie à la main
// plutôt que de laisser la personne dans une impasse.
//
// Variables d'environnement requises : SUPABASE_URL, SUPABASE_SECRET_KEY,
//   BREVO_API_KEY / BREVO_SENDER_EMAIL / ADMIN_NOTIFY_EMAIL (optionnel,
//   pour la notification en cas de non-correspondance)
//
// Route : /api/organisateur-claim (POST)

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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
  const { activite_id: activiteIdRaw, organisme: organismeRaw, email } = body || {};

  if (typeof email !== "string" || !EMAIL_RE.test(email)) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }
  const emailNorm = email.trim().toLowerCase();

  const headers = { apikey: secretKey, Authorization: `Bearer ${secretKey}` };

  let sourceKey, refActivite, lienSource;

  const activiteId = Number(activiteIdRaw);
  if (Number.isInteger(activiteId) && activiteId > 0) {
    const activiteRes = await fetch(
      `${supabaseUrl}/rest/v1/activites?select=id,nom_activite,organisateur,commune,lien_source&id=eq.${activiteId}`,
      { headers }
    );
    const activiteRows = await activiteRes.json();
    const activite = Array.isArray(activiteRows) ? activiteRows[0] : null;
    if (!activite) {
      return jsonResponse(404, { error: "Activité introuvable." });
    }
    sourceKey = activite.organisateur || activite.commune;
    refActivite = activite;
    lienSource = activite.lien_source;
    if (!sourceKey) {
      return jsonResponse(404, { error: "Cette activité n'est rattachée à aucun organisme identifiable." });
    }
  } else {
    const organisme = typeof organismeRaw === "string" ? organismeRaw.trim() : "";
    if (!organisme || organisme.length > 200) {
      return jsonResponse(400, { error: "Merci d'indiquer le nom de votre organisme." });
    }
    sourceKey = organisme;
    // Une activité de cet organisme suffit pour récupérer un domaine
    // source à comparer (voir create-checkout-session.js, même logique).
    const actRes = await fetch(
      `${supabaseUrl}/rest/v1/activites?select=id,nom_activite,lien_source&or=(organisateur.eq.${encodeURIComponent(organisme)},commune.eq.${encodeURIComponent(organisme)})&lien_source=not.is.null&limit=1`,
      { headers }
    );
    const actRows = await actRes.json();
    refActivite = Array.isArray(actRows) && actRows[0] ? actRows[0] : { nom_activite: null, id: null };
    lienSource = refActivite.lien_source;
  }

  const contactRes = await fetch(
    `${supabaseUrl}/rest/v1/organisateurs_contact?select=contact_email,access_token&source_key=eq.${encodeURIComponent(sourceKey)}`,
    { headers }
  );
  const contactRows = await contactRes.json();
  const existingContact = Array.isArray(contactRows) && contactRows[0] ? contactRows[0] : null;

  const verified = isAffiliated(emailNorm, [existingContact && existingContact.contact_email, lienSource]);

  if (!verified) {
    context.waitUntil(
      notifyUnverifiedClaim(env, supabaseUrl, secretKey, sourceKey, refActivite, emailNorm).catch((err) => {
        console.error("Notification de demande d'accès impossible", err);
      })
    );
    return jsonResponse(403, {
      error:
        "On n'a pas pu vérifier automatiquement que vous êtes bien affilié·e à cet organisme. Votre demande a été transmise, on vous recontacte rapidement.",
    });
  }

  // Réutilise le jeton existant s'il y en a déjà un (ex. déjà invité·e par
  // Muriel plus tôt) - sinon en génère un nouveau, exactement comme
  // admin-invite-organizer.js.
  let token = existingContact && existingContact.access_token;
  if (!token) {
    token = generateToken();
    const upsertRes = await fetch(`${supabaseUrl}/rest/v1/organisateurs_contact?on_conflict=source_key`, {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
        Prefer: "resolution=merge-duplicates,return=minimal",
      },
      body: JSON.stringify([{ source_key: sourceKey, contact_email: emailNorm, access_token: token }]),
    });
    if (!upsertRes.ok) {
      const details = await upsertRes.text().catch(() => "");
      console.error("Échec de création du contact/jeton", details);
      return jsonResponse(502, { error: "Une erreur est survenue, réessayez dans un instant." });
    }
  }

  return jsonResponse(200, { token });
}

export async function onRequest() {
  return jsonResponse(405, { error: "Méthode non autorisée." });
}

async function notifyUnverifiedClaim(env, supabaseUrl, secretKey, sourceKey, activite, email) {
  const via = activite && activite.id != null ? ` via l'activité "${activite.nom_activite}" (id ${activite.id})` : "";
  // Trace dans contact_requests (voir migration 20260903) même si la
  // notification email échoue ou n'est pas configurée - ne jamais perdre
  // une demande d'accès.
  await fetch(`${supabaseUrl}/rest/v1/contact_requests`, {
    method: "POST",
    headers: {
      apikey: secretKey,
      Authorization: `Bearer ${secretKey}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify([
      {
        type: "claim",
        email,
        message: `Demande d'accès non vérifiée pour "${sourceKey}"${via}.`,
      },
    ]),
  }).catch((err) => console.error("Écriture contact_requests impossible", err));

  const apiKey = env.BREVO_API_KEY;
  const senderEmail = env.BREVO_SENDER_EMAIL;
  const notifyEmail = env.ADMIN_NOTIFY_EMAIL;
  if (!apiKey || !senderEmail || !notifyEmail) return;

  const senderName = env.BREVO_SENDER_NAME || "Trouvéo";
  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": apiKey, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      sender: { name: senderName, email: senderEmail },
      to: [{ email: notifyEmail }],
      subject: `Trouvéo — demande d'accès à vérifier (${sourceKey})`,
      htmlContent:
        `<p><strong>${esc(email)}</strong> demande l'accès à l'espace organisateur de <strong>${esc(sourceKey)}</strong>` +
        (activite && activite.id != null ? `, via l'activité "${esc(activite.nom_activite)}" (id ${activite.id}).</p>` : ".</p>") +
        `<p>Son email ne correspond à aucun contact ou domaine déjà connu pour cet organisme - vérifie que c'est légitime avant d'agir.</p>` +
        `<p>Si oui : ajoute/mets à jour la ligne dans <code>organisateurs_contact</code> (source_key = "${esc(sourceKey)}", contact_email = "${esc(email)}"), puis invite via /api/admin-invite-organizer.</p>`,
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

// Même logique que create-checkout-session.js (dupliquée volontairement -
// pas de module partagé entre les fonctions Cloudflare dans ce dépôt).
function isAffiliated(email, references) {
  const emailDomain = domainOf(email);
  for (const ref of references) {
    if (!ref) continue;
    if (ref.includes("@")) {
      if (ref.trim().toLowerCase() === email) return true;
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

function esc(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function jsonResponse(statusCode, body) {
  return new Response(JSON.stringify(body), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}
