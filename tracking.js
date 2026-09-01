// Stagéo — tracking propriétaire minimal (voir docs plan d'exécution
// 01/09/2026, §6-11). Événements en liste blanche uniquement (voir
// functions/api/event.js), aucune donnée personnelle, jamais bloquant
// pour le parcours utilisateur.
//
// Session anonyme : sessionStorage plutôt que localStorage ou un cookie -
// choix délibéré (voir §9 du plan d'exécution) :
//   - sessionStorage expire tout seul à la fermeture de l'onglet/fenêtre,
//     donc ne devient jamais un identifiant permanent d'un visiteur -
//     exactement ce qu'on ne veut pas (pas de fingerprinting, pas de
//     device ID durable) ;
//   - localStorage survivrait indéfiniment entre les visites, ce qui
//     s'apparente de fait à un identifiant permanent - écarté pour cette
//     raison même si techniquement plus simple ;
//   - un cookie first-party n'apporterait rien ici (le tracking n'a besoin
//     d'aucune info envoyée automatiquement au serveur à chaque requête) et
//     ajoute une bannière/complexité RGPD pour un gain nul - écarté aussi.
// Valeur générée avec crypto.getRandomValues (aléatoire réel, pas dérivée
// de caractéristiques du navigateur).
(function(){
  var KEY = 'trouveo_session_id';

  function makeId(){
    try {
      var bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      return Array.from(bytes, function(b){ return b.toString(16).padStart(2, '0'); }).join('');
    } catch (e) {
      // repli si crypto indisponible (très ancien navigateur) - toujours
      // aléatoire, jamais dérivé d'une empreinte machine
      return 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'.replace(/x/g, function(){
        return Math.floor(Math.random() * 16).toString(16);
      });
    }
  }

  function sessionId(){
    try {
      var id = sessionStorage.getItem(KEY);
      if (!id) {
        id = makeId();
        sessionStorage.setItem(KEY, id);
      }
      return id;
    } catch (e) {
      return makeId(); // sessionStorage indisponible (navigation privée stricte) : un id par appel, tant pis
    }
  }

  // trouveoTrack(eventName, properties?, opts?) - opts.activiteId,
  // opts.organizerId. Ne renvoie rien, ne jette jamais, ne bloque jamais
  // la navigation : voir OUTBOUND_REGISTRATION_CLICK, appelé juste avant
  // de quitter la page.
  window.trouveoTrack = function(eventName, properties, opts){
    try {
      var payload = JSON.stringify({
        event_name: eventName,
        session_id: sessionId(),
        properties: properties || {},
        activite_id: (opts && opts.activiteId) || null,
        organizer_id: (opts && opts.organizerId) || null
      });
      var url = '/api/event';
      if (navigator.sendBeacon) {
        var blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon(url, blob);
      } else {
        fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true }).catch(function(){});
      }
    } catch (e) {
      // le tracking ne doit jamais faire échouer une action utilisateur
    }
  };
})();
