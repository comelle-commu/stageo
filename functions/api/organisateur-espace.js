// Renvoie les informations d'un organisme identifié par son jeton d'accès
// (voir supabase/migrations/20260902b_add_organizer_access_token.sql) -
// ses activités actuelles, leur statut Boost, et son statut Partenaire.
// Lu par organisateur.html.
//
// Le jeton lui-même EST l'authentification (comme le lien de
// désinscription) : quiconque le possède est considéré être cet
// organisme, sans mot de passe séparé - voir le commentaire de la
// colonne access_token pour le raisonnement complet.
//
// Variables d'environnement requises : SUPABASE_URL, SUPABASE_SECRET_KEY
//
// Route : /api/organisateur-espace?token=...

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const token = url.searchParams.get("token");

  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secretKey) {
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }
  if (!token) {
    return jsonResponse(400, { error: "Lien invalide." });
  }

  const headers = { apikey: secretKey, Authorization: `Bearer ${secretKey}` };

  const contactRes = await fetch(
    `${supabaseUrl}/rest/v1/organisateurs_contact?select=source_key,contact_email&access_token=eq.${encodeURIComponent(token)}`,
    { headers }
  );
  const contactRows = await contactRes.json();
  const contact = Array.isArray(contactRows) ? contactRows[0] : null;
  if (!contact) {
    return jsonResponse(404, { error: "Lien invalide ou expiré. Écrivez à hello@trouveo.be si besoin." });
  }
  const sourceKey = contact.source_key;

  // Même convention que groupKey() côté client / relance_organisateurs.py :
  // un organisme est identifié par `organisateur`, ou par `commune` pour
  // les sources communales sans champ organisateur distinct.
  const activitesRes = await fetch(
    `${supabaseUrl}/rest/v1/activites?select=id,nom_activite,dates,lieu,prix,age_min,age_max,lien_source` +
      `&or=(organisateur.eq.${encodeURIComponent(sourceKey)},commune.eq.${encodeURIComponent(sourceKey)})` +
      `&order=dates.desc&limit=200`,
    { headers }
  );
  const activites = await activitesRes.json();

  const activiteIds = (Array.isArray(activites) ? activites : []).map((a) => a.id);
  let boostRows = [];
  if (activiteIds.length) {
    const inList = activiteIds.join(",");
    const boostRes = await fetch(
      `${supabaseUrl}/rest/v1/activites_boost?select=activite_id,boost_jusquau&activite_id=in.(${inList})`,
      { headers }
    );
    boostRows = await boostRes.json();
  }
  const boostMap = {};
  (Array.isArray(boostRows) ? boostRows : []).forEach((b) => {
    boostMap[b.activite_id] = b.boost_jusquau;
  });

  const premiumRes = await fetch(
    `${supabaseUrl}/rest/v1/organismes_premium?select=mis_en_avant_jusquau,mise_en_avant_complete&source_key=eq.${encodeURIComponent(sourceKey)}`,
    { headers }
  );
  const premiumRows = await premiumRes.json();
  const premium = Array.isArray(premiumRows) ? premiumRows[0] || null : null;

  return jsonResponse(200, {
    source_key: sourceKey,
    contact_email: contact.contact_email,
    activites: (Array.isArray(activites) ? activites : []).map((a) => ({
      ...a,
      boost_jusquau: boostMap[a.id] || null,
    })),
    partenaire: premium
      ? { jusquau: premium.mis_en_avant_jusquau, complet: !!premium.mise_en_avant_complete }
      : null,
  });
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
