// Bilan d'un Boost (voir docs plan d'exécution §16, "Mesure du ROI d'un
// Boost") : compare vues/clics pendant le boost à la même durée juste
// avant. Même protection par jeton que admin-stats.js - jamais de clé
// secrète exposée au navigateur.
//
// Route : /api/boost-report?activite_id=123&key=VOTRE_JETON
//
// Important (voir consigne §15 du plan d'exécution) : si le volume
// "avant" est trop faible pour être significatif, on ne calcule PAS de
// pourcentage spectaculaire et trompeur - on le dit explicitement.
const MIN_BEFORE_FOR_PERCENT = 5; // en dessous, une variation en % ne veut rien dire

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  if (!env.ADMIN_TOKEN || url.searchParams.get("key") !== env.ADMIN_TOKEN) {
    return jsonResponse(403, { error: "Accès refusé." });
  }
  const activiteId = Number(url.searchParams.get("activite_id"));
  if (!Number.isInteger(activiteId)) {
    return jsonResponse(400, { error: "activite_id manquant ou invalide." });
  }

  const supabaseUrl = env.SUPABASE_URL;
  const secretKey = env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secretKey) {
    return jsonResponse(500, { error: "Configuration serveur incomplète." });
  }
  const headers = { apikey: secretKey, Authorization: `Bearer ${secretKey}` };
  const sb = (path) => fetch(`${supabaseUrl}/rest/v1/${path}`, { headers }).then((r) => (r.ok ? r.json() : []));

  const boostRows = await sb(`activites_boost?select=boost_debute_le,boost_jusquau&activite_id=eq.${activiteId}`);
  if (!boostRows.length) {
    return jsonResponse(404, { error: "Aucun boost enregistré pour cette activité." });
  }
  const { boost_debute_le, boost_jusquau } = boostRows[0];

  const debut = new Date(boost_debute_le + "T00:00:00Z");
  const fin = new Date(Math.min(new Date(boost_jusquau + "T23:59:59Z").getTime(), Date.now()));
  const dureeMs = fin - debut;
  const avantDebut = new Date(debut.getTime() - dureeMs);
  const avantFin = debut;

  const [viewsPendant, clicksPendant, viewsAvant, clicksAvant] = await Promise.all([
    sb(`events?select=id&event_name=eq.ACTIVITY_VIEWED&activite_id=eq.${activiteId}&created_at=gte.${debut.toISOString()}&created_at=lte.${fin.toISOString()}`),
    sb(`events?select=id&event_name=eq.OUTBOUND_REGISTRATION_CLICK&activite_id=eq.${activiteId}&created_at=gte.${debut.toISOString()}&created_at=lte.${fin.toISOString()}`),
    sb(`events?select=id&event_name=eq.ACTIVITY_VIEWED&activite_id=eq.${activiteId}&created_at=gte.${avantDebut.toISOString()}&created_at=lt.${avantFin.toISOString()}`),
    sb(`events?select=id&event_name=eq.OUTBOUND_REGISTRATION_CLICK&activite_id=eq.${activiteId}&created_at=gte.${avantDebut.toISOString()}&created_at=lt.${avantFin.toISOString()}`),
  ]);

  const vP = viewsPendant.length, cP = clicksPendant.length;
  const vA = viewsAvant.length, cA = clicksAvant.length;
  const ctrPendant = vP ? ((cP / vP) * 100).toFixed(1) : null;
  const ctrAvant = vA ? ((cA / vA) * 100).toFixed(1) : null;

  let comparaison;
  if (vA >= MIN_BEFORE_FOR_PERCENT) {
    const variation = Math.round(((vP - vA) / vA) * 100);
    comparaison = `${variation >= 0 ? "+" : ""}${variation}% de vues par rapport aux ${Math.round(dureeMs / 86400000)} jours précédents.`;
  } else {
    comparaison = "Pas assez de données sur la période précédente pour comparer de façon fiable - les chiffres bruts ci-dessous restent valables.";
  }

  return jsonResponse(200, {
    activite_id: activiteId,
    periode_boost: { debut: boost_debute_le, fin: boost_jusquau },
    pendant: { vues: vP, clics: cP, ctr: ctrPendant },
    avant: { vues: vA, clics: cA, ctr: ctrAvant },
    resume: comparaison,
  });
}

function jsonResponse(statusCode, body) {
  return new Response(JSON.stringify(body, null, 2), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}
