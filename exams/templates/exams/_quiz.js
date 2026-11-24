{% load bn %}
var BN='{% t "০১২৩৪৫৬৭৮৯" %}', LET={a:'{% t "ক" %}',b:'{% t "খ" %}',c:'{% t "গ" %}',d:'{% t "ঘ" %}'}, toBn=function(n){return String(n).replace(/\d/g,function(d){return BN[d]})};
var streak=0, pts=0;
function bump(id,val){ var e=document.getElementById(id); if(e){ e.textContent=toBn(val); e.classList.remove('bump'); void e.offsetWidth; e.classList.add('bump'); } }
function answer(card,b){
  if(card.dataset.done) return; card.dataset.done=1;
  var right=card.dataset.correct, ok=b.dataset.k===right;
  card.querySelectorAll('.opt').forEach(function(o){ o.disabled=true; if(o.dataset.k===right) o.classList.add('right'); });
  if(!ok) b.classList.add('wrong');
  var n=card.querySelector('.note'); if(n){ n.hidden=false; }
  streak=ok?streak+1:0; if(ok) pts+=10;
  bump('h-streak',streak); bump('h-pts',pts); bump('t-streak',streak); bump('t-pts',pts);
  var t=window.tally; if(t){ t.done++; if(ok) t.ok++; document.getElementById('t-ok').textContent=toBn(t.ok); document.getElementById('t-no').textContent=toBn(t.done-t.ok);
    document.getElementById('t-bar').style.width=(100*t.ok/t.done)+'%'; document.getElementById('t-pct').textContent=toBn(Math.round(100*t.ok/t.done))+'%'; }
}
function bind(card){ card.querySelectorAll('.opt').forEach(function(b){ b.addEventListener('click',function(){ answer(card,b); }); }); }
document.querySelectorAll('.pq').forEach(bind);
// "next question" on the home card: fetch another random question and swap it in
document.querySelectorAll('.pq[data-next]').forEach(function(card){
  var btn=card.querySelector('.nextq'); if(!btn) return;
  btn.addEventListener('click',function(){
    btn.disabled=true;
    fetch(card.dataset.next+'?exclude='+card.dataset.qid).then(function(r){return r.json()}).then(function(q){
      btn.disabled=false; if(q.empty) return;
      card.dataset.qid=q.id; card.dataset.correct=q.correct; delete card.dataset.done;
      card.querySelector('.subj').textContent=q.subject; card.querySelector('.qtext').textContent=q.text;
      card.querySelectorAll('.opt').forEach(function(o){o.remove()});
      var note=card.querySelector('.note'), strong=note.querySelector('b');
      q.options.forEach(function(o){ var el=document.createElement('button'); el.type='button'; el.className='opt'; el.dataset.k=o.k;
        var bub=document.createElement('span'); bub.className='bub'; bub.textContent=LET[o.k]; var tx=document.createElement('span'); tx.textContent=o.v;
        el.append(bub,tx); card.insertBefore(el,note); });
      strong.textContent='{% t "সঠিক উত্তর: " %}'+LET[q.correct]; var ex=note.querySelector('.ex'); ex.textContent=q.explanation?(' — '+q.explanation):'';
      note.hidden=true; bind(card); card.classList.remove('swap'); void card.offsetWidth; card.classList.add('swap');
    }).catch(function(){btn.disabled=false});
  });
});
