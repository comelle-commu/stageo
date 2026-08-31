// Relais entre le formulaire de criteres.html ("vos critères de
// recherche") et la table Supabase `criteres_parents`.
//
// Même raison d'être qu'un relais serveur que brevo-signup.js/
// contact-request.js : la clé secrète Supabase ne doit jamais être
// envoyée au navigateur.
//
// Variables d'environnement requises (Cloudflare Pages → Settings →
// Environment variables) :
//   SUPABASE_URL         - même valeur que dans scrapers/.env
//   SUPABASE_SECRET_KEY   - idem (clé secrète, PAS la clé publique côté client)
//   BREVO_API_KEY         - idem (voir criteres_alertes.py, même clé)
//   BREVO_SENDER_EMAIL    - idem
//   BREVO_SENDER_NAME     - optionnel, "Trouvéo" par défaut
//
// Route : fichier functions/api/save-criteria.js -> disponible sur /api/save-criteria
//
// Upsert sur `email` (on_conflict) : une personne qui republie le
// formulaire (ex. pour ajouter un enfant) met à jour sa ligne existante
// plutôt que d'en créer une deuxième - même logique que updateEnabled
// côté Brevo pour la liste d'attente simple.
//
// Après l'upsert, un email de confirmation récapitulatif est envoyé (API
// transactionnelle Brevo, même mécanisme que criteres_alertes.py) : sans
// ça, un parent qui remplit ce formulaire n'a plus AUCUN signal que
// l'enregistrement a marché une fois quitté la page (la confirmation
// visuelle sur criteres.html ne suffit pas si on a un doute après coup, ou
// si on l'a rempli sur mobile sans vraiment regarder l'écran final) - voir
// le cas d'angekellya@gmail.com qui a renvoyé ses critères par message
// faute d'avoir eu confirmation par email. Un échec d'envoi ne doit
// jamais faire échouer l'enregistrement : celui-ci reste la partie
// importante, l'email n'est qu'un plus.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const VALID_TYPES = new Set(["Sport", "Art & créativité", "Sciences & nature", "Langues", "Multi-activités"]);
const MAX_ENFANTS = 5;

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

  const { email, enfants, commune } = body || {};

  if (typeof email !== "string" || !EMAIL_RE.test(email)) {
    return jsonResponse(400, { error: "Adresse email invalide." });
  }
  if (!Array.isArray(enfants) || enfants.length === 0 || enfants.length > MAX_ENFANTS) {
    return jsonResponse(400, { error: `Merci d'indiquer entre 1 et ${MAX_ENFANTS} enfant(s).` });
  }
  // Chaque enfant porte ses propres types d'activités (pas un choix
  // partagé pour toute la fratrie) - un enfant peut vouloir du sport
  // pendant qu'un autre préfère l'art, d'où ce champ par enfant plutôt
  // qu'un `types_activites` unique au niveau de la famille.
  for (const enfant of enfants) {
    const age = enfant && enfant.age;
    if (typeof age !== "number" || Number.isNaN(age) || age < 2 || age > 18) {
      return jsonResponse(400, { error: "Chaque âge doit être compris entre 2 et 18 ans." });
    }
    const types = Array.isArray(enfant.types_activites) ? enfant.types_activites : [];
    if (!types.every((t) => VALID_TYPES.has(t))) {
      return jsonResponse(400, { error: "Type d'activité invalide." });
    }
  }
  if (typeof commune !== "string" || !commune.trim() || commune.trim().length > 120) {
    return jsonResponse(400, { error: "Merci d'indiquer une localité." });
  }

  try {
    const res = await fetch(`${supabaseUrl}/rest/v1/criteres_parents?on_conflict=email`, {
      method: "POST",
      headers: {
        apikey: secretKey,
        Authorization: `Bearer ${secretKey}`,
        "Content-Type": "application/json",
        Prefer: "resolution=merge-duplicates,return=minimal",
      },
      body: JSON.stringify([
        {
          email,
          enfants: enfants.map((e) => ({
            age: e.age,
            types_activites: Array.isArray(e.types_activites) ? e.types_activites : [],
          })),
          commune: commune.trim(),
          rayon_km: 15,
          updated_at: new Date().toISOString(),
        },
      ]),
    });

    // 201 = nouvelle ligne créée, 204 = ligne mise à jour selon les cas -
    // mais PostgREST répond aussi 200 pour une mise à jour via
    // on_conflict+merge-duplicates (constaté en pratique, contrairement à
    // brevo-signup.js où seuls 201/204 apparaissent) : un email qui
    // republie le formulaire (ex. pour corriger un âge) tombait donc à
    // tort dans la branche d'erreur ci-dessous.
    if (res.status === 200 || res.status === 201 || res.status === 204) {
      // Best-effort : une erreur d'envoi ne doit pas transformer un
      // enregistrement réussi en échec côté utilisateur.
      await sendConfirmationEmail(env, email, enfants, commune.trim()).catch((err) => {
        console.error("Envoi de l'email de confirmation impossible", err);
      });
      return jsonResponse(200, { ok: true });
    }

    const details = await res.text().catch(() => "");
    console.error("Réponse Supabase inattendue", res.status, details);
    return jsonResponse(502, { error: "L'enregistrement a échoué, réessayez dans un instant." });
  } catch (err) {
    console.error("Appel à Supabase impossible", err);
    return jsonResponse(502, { error: "L'enregistrement a échoué, réessayez dans un instant." });
  }
}

function esc(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Doit rester synchronisé avec AGE_BRACKETS dans activites.html et
// criteres_alertes.py (build_detail_link) - même logique de lien
// pré-filtré que les emails d'alerte : la commune (recherche par
// proximité déjà en place côté site), l'âge SEULEMENT pour une famille à
// un enfant (un chip d'âge unique représenterait mal une fratrie
// d'âges différents), et l'union dédupliquée des types de tous les
// enfants (une préférence qui se cumule, contrairement à l'âge).
const AGE_BRACKETS = [
  [0, 3],
  [3, 6],
  [6, 9],
  [9, 12],
  [12, Infinity],
];

function buildDetailLink(enfants, commune) {
  const params = new URLSearchParams({ commune });
  if (enfants.length === 1) {
    const age = enfants[0].age;
    if (typeof age === "number" && AGE_BRACKETS.some(([lo, hi]) => age >= lo && age < hi)) {
      params.set("age", String(age));
    }
  }
  const allTypes = [];
  for (const enfant of enfants) {
    for (const t of enfant.types_activites || []) {
      if (!allTypes.includes(t)) allTypes.push(t);
    }
  }
  if (allTypes.length) {
    params.set("types", allTypes.join(","));
  }
  return `https://trouveo.be/activites?${params.toString()}`;
}

async function sendConfirmationEmail(env, email, enfants, commune) {
  const apiKey = env.BREVO_API_KEY;
  const senderEmail = env.BREVO_SENDER_EMAIL;
  if (!apiKey || !senderEmail) {
    console.error("BREVO_API_KEY ou BREVO_SENDER_EMAIL manquant - email de confirmation ignoré");
    return;
  }
  const senderName = env.BREVO_SENDER_NAME || "Trouvéo";
  const detailLink = buildDetailLink(enfants, commune);

  const rows = enfants
    .map((e) => {
      const types = Array.isArray(e.types_activites) && e.types_activites.length
        ? e.types_activites.join(", ")
        : "tous types d'activités";
      return (
        '<tr><td style="padding:0 0 8px;color:#015380;font-size:14.5px;line-height:1.5;">' +
        // age >= 2 toujours (validé plus haut) -> pluriel systématique.
        `• ${e.age} ans — ${esc(types)}</td></tr>`
      );
    })
    .join("");

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
      Vos critères sont bien enregistrés
    </span>
  </td></tr>

  <tr><td style="padding-bottom:18px;color:#5C7A8C;font-size:14.5px;line-height:1.6;">
    Nous surveillons désormais les nouveaux stages et activités qui correspondent à ces critères,
    et vous préviendrons par email dès qu'une place correspond.
  </td></tr>

  <tr><td style="padding:14px 16px;background:#FFFFFF;border:1px solid rgba(1,83,128,0.12);border-radius:14px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="padding:0 0 8px;color:#93A9B5;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">Localité</td></tr>
      <tr><td style="padding:0 0 14px;color:#015380;font-size:14.5px;">${esc(commune)} (rayon de 15 km)</td></tr>
      <tr><td style="padding:0 0 8px;color:#93A9B5;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;">Enfant${enfants.length > 1 ? "s" : ""}</td></tr>
      ${rows}
    </table>
  </td></tr>

  <tr><td align="center" style="padding:26px 0 8px;">
    <a href="${detailLink}" style="display:inline-block;background:#0197AF;color:#ffffff;text-decoration:none;
      font-family:'Work Sans',Arial,sans-serif;font-weight:700;font-size:14px;padding:14px 28px;border-radius:100px;">
      Parcourir les activités →
    </a>
  </td></tr>

  <tr><td style="border-top:1px solid rgba(1,83,128,0.12);padding-top:18px;margin-top:14px;">
    <p style="color:#93A9B5;font-size:12px;line-height:1.6;margin:0;text-align:center;">
      Une erreur dans vos critères ? Remplissez à nouveau le formulaire reçu par email, ou écrivez-nous à hello@trouveo.be.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>`;

  // Timeout explicite : sans ça, un Brevo lent ou injoignable ferait
  // traîner toute la réponse HTTP jusqu'à ce que la plateforme Cloudflare
  // tue elle-même la requête (502 générique, sans passer par notre
  // gestion d'erreur ci-dessus) - inacceptable pour un email qui n'est
  // qu'un plus par rapport à l'enregistrement déjà réussi en base.
  const resp = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": apiKey, "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      sender: { name: senderName, email: senderEmail },
      to: [{ email }],
      subject: "Vos critères sont bien enregistrés",
      htmlContent: html,
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
