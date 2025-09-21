
(function(){
  if (window.__KISDIAG_LAUNCHED__) return; window.__KISDIAG_LAUNCHED__=true;
  function openDiag(){ var base = window.location.origin.replace(/:\d+$/, ':8000'); window.open(base + '/_kisdiag/ui', '_blank'); }
  var btn = document.createElement('button');
  btn.textContent = 'KIS 진단';
  btn.style.position='fixed'; btn.style.right='18px'; btn.style.bottom='18px';
  btn.style.padding='10px 14px'; btn.style.borderRadius='20px';
  btn.style.border='1px solid #334'; btn.style.background='#141b2d'; btn.style.color='#cfe3ff';
  btn.style.cursor='pointer'; btn.style.zIndex=2147483647; btn.style.boxShadow='0 4px 10px rgba(0,0,0,.25)';
  btn.onclick=openDiag;
  document.addEventListener('keydown', function(e){ if ((e.ctrlKey||e.metaKey) && e.shiftKey && e.code==='KeyD') openDiag(); });
  var tryAppend = function(){
    if (document.body) document.body.appendChild(btn); else setTimeout(tryAppend, 500);
  };
  tryAppend();
})();
