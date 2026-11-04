/* 直問！ Day の問題を「答えて進む」仕組み（公開サイトの Day 1〜10 と、会員サイトの全 Day で共通）
   ・選択肢を押すと答えが決まり、正解でも不正解でも、その問題の答えと解説が開く（答えは1回だけ・あとから変えられない）
   ・全部の問題に答えると、その Day が「終わった」ことになる
   ・Day は全員共通の日程で、毎日20時（日本時間）に1つずつ開く（Day N は 2026/11/3 20:00 から N-1 日後）
   ・前の Day を全部終えていないと、次の Day は開けない
   data-mode="local"：公開サイト。記録はこの端末（ブラウザ）の中だけ
   data-mode="server"：会員サイト。記録はアカウントに（POST /day/N/answer） */
(function () {
  var me = document.currentScript;
  var MODE = (me && me.dataset.mode) || "local";
  var DAY = +(me && me.dataset.day) || 0;
  var MAXFREE = +(me && me.dataset.max) || 10;
  var MAXDAY = +(me && me.dataset.maxday) || 0;   // 会員サイト：いま用意されている Day の数
  var BASE = Date.parse("2026-11-03T20:00:00+09:00");
  var releaseAt = function (d) { return BASE + (d - 1) * 86400000; };
  var released = function (d) { return Date.now() >= releaseAt(d); };
  var jaTime = function (ms) { var t = new Date(ms + 9 * 3600000); return (t.getUTCMonth() + 1) + "月" + t.getUTCDate() + "日 20:00"; };
  var store = {
    get: function (k) { try { return JSON.parse(localStorage.getItem("chokumon:" + k) || "null"); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem("chokumon:" + k, JSON.stringify(v)); } catch (e) {} },
  };
  var doneLocal = function (d) { return !!store.get("done:d" + d); };

  var css = document.createElement("style");
  css.textContent =
    ".q:not(.answered) details{display:none}" +
    ".q .opts li.pick{cursor:pointer;transition:background .15s,border-color .15s}.q:not(.answered) .opts li.pick{border-color:rgba(255,255,255,.14);margin-bottom:2px}" +
    ".q:not(.answered) .opts li.pick:hover{border-color:rgba(255,255,255,.28);background:rgba(255,255,255,.04)}" +
    ".q:not(.answered) .opts li.pick:focus-visible{outline:2px solid #FF6A1A;outline-offset:2px}" +
    ".q.answered .opts li.ok{border-color:#3DD68C!important;background:rgba(61,214,140,.13)!important}" +
    ".q.answered .opts li.mine:not(.ok){border-color:#FF6464!important;background:rgba(255,100,100,.12)!important}" +
    ".q.answered .opts li{cursor:default}" +
    ".vd{margin:10px 0 0 42px;font-weight:700;font-size:15px;display:flex;align-items:center;gap:8px}" +
    ".vd.r{color:#3DD68C}.vd.w{color:#FF8A8A}.vd span{font-weight:500;color:#BDBDBD;font-size:14px}" +
    ".qhint{margin:8px 0 0 42px;font-size:13px;color:#A6A6A6}" +
    ".dprog{position:sticky;top:0;z-index:15;display:flex;align-items:center;gap:12px;margin:14px 0;padding:10px 14px;border-radius:14px;background:rgba(18,18,18,.94);border:1px solid #2B2B2B;backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}" +
    ".dprog b{font-family:Sora,sans-serif;font-variant-numeric:tabular-nums;white-space:nowrap}.dprog .bar{flex:1;height:8px;border-radius:4px;background:#2B2B2B;overflow:hidden}" +
    ".dprog .bar i{display:block;height:100%;background:#FF6A1A;border-radius:4px;transition:width .3s}" +
    ".dfin{margin:24px 0;padding:18px;border-radius:16px;border:1.5px solid #3DD68C;background:rgba(61,214,140,.08)}" +
    ".dfin b{display:block;font-size:19px;margin-bottom:4px}.dfin p{margin:6px 0;color:#DADADA;font-size:14.5px}" +
    ".dfin a,.dlock a{display:inline-block;margin-top:10px;padding:11px 18px;border-radius:999px;background:#FF6A1A;color:#000;font-weight:700;text-decoration:none}" +
    ".dlock{margin:22px 0;padding:22px 18px;border-radius:16px;border:1.5px solid #FF6A1A;background:#0b0b0b;text-align:center}" +
    ".dlock b{display:block;font-size:19px;margin-bottom:6px}.dlock p{margin:4px 0;color:#DADADA;font-size:14.5px}" +
    ".days a.locked{opacity:.45}.days a.fin{border-color:#3DD68C!important;color:#3DD68C}" +
    "@media (prefers-reduced-motion:reduce){.dprog .bar i{transition:none}}";
  document.head.appendChild(css);

  // ---- 公開サイト：Day の番号ボタン・一覧に「済・まだ開いていない」をつける ----
  if (MODE === "local") {
    document.querySelectorAll("a[href]").forEach(function (a) {
      var m;
      try { m = new URL(a.href, location.href).pathname.match(/^\/days\/(\d+)\/$/); } catch (e) { m = null; }
      if (!m) return;
      var d = +m[1], st = doneLocal(d) ? "fin" : !released(d) ? "wait" : d > 1 && !doneLocal(d - 1) ? "prev" : "open";
      if (st === "fin") a.classList.add("fin");
      else if (st !== "open") a.classList.add("locked");
      if (a.closest(".hub")) {   // 一覧ページ：それぞれの Day の状態を1行で
        var t = document.createElement("small");
        t.style.color = st === "fin" ? "#3DD68C" : st === "open" ? "#FF6A1A" : "";
        t.textContent = st === "fin" ? "✓ 終わりました" : st === "wait" ? jaTime(releaseAt(d)) + " に開きます" : st === "prev" ? "前の Day を終えると開きます" : "いま解けます";
        a.appendChild(t);
      }
    });
  }

  var root = document.querySelector(".day");
  if (!root || !DAY) return;
  var qs = [].slice.call(root.querySelectorAll("article.q"));
  if (!qs.length) return;

  // ---- 公開サイト：まだ開いていない Day・前の Day が終わっていないときは、問題を出さない ----
  if (MODE === "local") {
    var why = "";
    if (!released(DAY)) why = "<b>Day " + DAY + " は " + jaTime(releaseAt(DAY)) + " に開きます</b><p>Day は毎日20時に1つずつ開きます。</p>" + (DAY > 1 ? '<a href="/days/' + (DAY - 1) + '/">Day ' + (DAY - 1) + " にもどる</a>" : "");
    else if (DAY > 1 && !doneLocal(DAY - 1)) why = "<b>先に Day " + (DAY - 1) + " を終わらせましょう</b><p>前の Day の問題に全部答えると、Day " + DAY + " に進めます。</p><p style=\"font-size:13px;color:#A6A6A6\">記録はこの端末（ブラウザ）の中にあります。別の端末では、もう一度 Day 1 からになります。</p><a href=\"/days/" + (DAY - 1) + "/\">Day " + (DAY - 1) + " へ</a>";
    if (why) {
      root.hidden = true;
      var lk = document.createElement("div");
      lk.className = "dlock";
      lk.innerHTML = why;
      root.parentNode.insertBefore(lk, root);
      return;
    }
  }

  var saved = MODE === "local" ? store.get("ans:d" + DAY) || {} : (window.CHOKU_ANS || {});
  var prog = document.createElement("div");
  prog.className = "dprog";
  prog.setAttribute("role", "status");
  root.insertBefore(prog, root.querySelector("section, article") || root.firstChild);
  var fin = document.createElement("div");
  fin.className = "dfin";
  fin.hidden = true;
  root.appendChild(fin);

  var sendNo = 0, serverDoneSeen = false;
  function letter(k) { return "(" + "ABCD".charAt(k) + ")"; }
  function update(serverDone) {
    var n = 0, r = 0;
    qs.forEach(function (q) { if (q.classList.contains("answered")) { n++; if (q.classList.contains("right")) r++; } });
    prog.innerHTML = "<b>" + n + " / " + qs.length + " 問</b><span class=\"bar\"><i style=\"width:" + Math.round((n / qs.length) * 100) + "%\"></i></span><b>正解 " + r + "</b>";
    var all = n === qs.length;
    if (all) {
      var nx = DAY + 1, html = "<b>Day " + DAY + " が終わりました！</b><p>" + qs.length + "問中 " + r + "問 正解。まちがえた問題は、解説の英文を前から声に出して読みましょう。</p>";
      if (MODE === "local") {
        store.set("done:d" + DAY, 1);
        if (DAY >= MAXFREE) html += '<p>無料の問題はここまでです。Day 11 からは月額プランで、毎日20時に1日分ずつ開きます。</p><a href="/#plan">月額プランを見る</a>';
        else if (released(nx)) html += '<a href="/days/' + nx + '/">Day ' + nx + " へ進む</a>";
        else html += "<p>次の Day " + nx + " は " + jaTime(releaseAt(nx)) + " に開きます。</p>";
      } else {
        if (serverDone === false) html = "<b>記録しています…</b>";
        else if (nx > MAXDAY) html += "<p>いま用意されている Day はここまでです。</p>";
        else if (released(nx)) html += '<a href="/day/' + nx + '">Day ' + nx + " へ進む</a>";
        else if (!released(nx)) html += "<p>次の Day " + nx + " は " + jaTime(releaseAt(nx)) + " に開きます。</p>";
      }
      fin.innerHTML = html;
      fin.hidden = false;
    }
    return all;
  }
  function show(q, k, quiet) {
    var lis = q.querySelectorAll(".opts li"), okLi = q.querySelector(".opts li.ok");
    var okK = okLi ? +okLi.dataset.k : -1, right = k === okK;
    q.classList.add("answered", right ? "right" : "wrong");
    lis.forEach(function (li) { li.setAttribute("aria-disabled", "true"); li.removeAttribute("tabindex"); if (+li.dataset.k === k) li.classList.add("mine"); });
    var vd = document.createElement("p");
    vd.className = "vd " + (right ? "r" : "w");
    vd.innerHTML = right ? "○ 正解！" : "× 不正解 <span>正解は " + letter(okK) + "</span>";
    q.querySelector(".opts").insertAdjacentElement("afterend", vd);
    var h = q.querySelector(".qhint");
    if (h) h.remove();
    var det = q.querySelector("details");
    if (det) det.open = true;
    if (!quiet && det) setTimeout(function () { vd.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, 50);
  }
  function send(q, k) {
    if (MODE === "local") { saved[q.id] = k; store.set("ans:d" + DAY, saved); update(); return; }
    var my = ++sendNo;
    update(false);
    var fail = function (why) { prog.innerHTML = "<b>記録できませんでした。" + why + "</b>"; if (!fin.hidden) fin.innerHTML = "<b>記録できませんでした</b><p>" + why + "</p>"; };
    fetch("/day/" + DAY + "/answer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q: q.id, k: k }), credentials: "same-origin" })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (x) {
        if (!x.ok) return fail(x.j.error === "member" ? "会員の期間が終わっています。アカウントの画面を確かめてください。" : x.j.error === "locked" ? "この Day はまだ開いていないか、前の Day が終わっていません。" : "ページを開き直してから、もう一度答えてください。");
        if (x.j.done) serverDoneSeen = true;
        if (my === sendNo || serverDoneSeen) update(serverDoneSeen || (x.j.answered >= x.j.total));
      })
      .catch(function () { fail("通信を確かめて、ページを開き直してください。"); });
  }
  qs.forEach(function (q) {
    var lis = q.querySelectorAll(".opts li");
    if (saved[q.id] != null) { show(q, +saved[q.id], true); return; }
    var hint = document.createElement("p");
    hint.className = "qhint";
    hint.textContent = "答えを1つ選ぶと、答えと解説が開きます（選び直しはできません）";
    q.querySelector(".opts").insertAdjacentElement("afterend", hint);
    lis.forEach(function (li) {
      li.classList.add("pick");
      li.setAttribute("role", "button");
      li.setAttribute("tabindex", "0");
      var pick = function () { if (q.classList.contains("answered")) return; var k = +li.dataset.k; show(q, k); send(q, k); };
      li.addEventListener("click", pick);
      li.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    });
  });
  update();
})();
