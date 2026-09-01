// Stagéo — consentement minimal avant chargement du Meta Pixel (voir
// docs plan d'exécution 01/09/2026, §18 RGPD). Le Meta Pixel dépose un
// cookie tiers utilisé à des fins publicitaires : il ne doit se charger
// qu'après acceptation explicite, jamais par défaut. Cloudflare Web
// Analytics n'est pas concerné (pas de cookie, pas de tracking
// cross-site) et continue de se charger sans bannière.
//
// Choix volontairement minimal : un seul choix binaire (accepter /
// refuser), pas de gestionnaire de préférences par finalité - proportionné
// à un seul cookie tiers non essentiel, pas à une dizaine d'outils.
// Stocké dans localStorage (pas un cookie) : purement une préférence
// d'affichage de CE navigateur, jamais envoyée au serveur.
//
// Inclus sur chaque page via <script src="consent.js"></script>, PLACÉ
// AVANT le bloc Meta Pixel - voir initMetaPixelIfConsented() ci-dessous,
// appelée depuis chaque page à la place de l'ancien appel direct à fbq().
(function(){
  var KEY = 'trouveo_consent_pixel';

  function getConsent(){
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function setConsent(value){
    try { localStorage.setItem(KEY, value); } catch (e) {}
  }

  window.trouveoConsent = {
    // Appelée par le bloc Meta Pixel de chaque page : charge fbq()
    // immédiatement si déjà accepté, sinon attend la bannière.
    initMetaPixelIfConsented: function(loadFn){
      var v = getConsent();
      if (v === 'accepted') { loadFn(); return; }
      if (v === 'refused') { return; }
      window.trouveoConsent._pendingLoad = loadFn;
      showBanner();
    }
  };

  function showBanner(){
    // consent.js est chargé dans <head>, avant que <body> existe : si le
    // DOM n'est pas encore prêt, on retente au bon moment plutôt que de
    // planter sur document.body.appendChild(null).
    if (!document.body) {
      document.addEventListener('DOMContentLoaded', showBanner, { once: true });
      return;
    }
    if (document.getElementById('consentBanner')) return;
    var el = document.createElement('div');
    el.id = 'consentBanner';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', 'Cookies');
    el.style.cssText = 'position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;'
      + 'max-width:520px;margin:0 auto;background:#015380;color:#FFFDF8;'
      + 'font-family:"Work Sans",Arial,sans-serif;font-size:13.5px;line-height:1.5;'
      + 'padding:16px 18px;border-radius:14px;box-shadow:0 14px 34px -12px rgba(0,0,0,0.4);'
      + 'display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;';
    el.innerHTML =
      '<span style="flex:1;min-width:220px;">Trouvéo utilise un cookie de mesure publicitaire (Meta) - uniquement si vous l\'acceptez. <a href="/confidentialite.html" style="color:#FFFDF8;text-decoration:underline;">En savoir plus</a></span>'
      + '<span style="display:flex;gap:8px;flex:none;">'
      + '<button id="consentRefuse" type="button" style="background:transparent;color:#FFFDF8;border:1px solid rgba(255,253,248,0.5);padding:8px 14px;border-radius:100px;font-size:13px;font-weight:600;cursor:pointer;">Refuser</button>'
      + '<button id="consentAccept" type="button" style="background:#0197AF;color:#fff;border:none;padding:8px 16px;border-radius:100px;font-size:13px;font-weight:700;cursor:pointer;">Accepter</button>'
      + '</span>';
    document.body.appendChild(el);
    document.getElementById('consentAccept').addEventListener('click', function(){
      setConsent('accepted');
      el.remove();
      if (window.trouveoConsent._pendingLoad) window.trouveoConsent._pendingLoad();
    });
    document.getElementById('consentRefuse').addEventListener('click', function(){
      setConsent('refused');
      el.remove();
    });
  }
})();
