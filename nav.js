/* スマホ用メニュー：左上の三本線を押すと、左からメニューが出る（全ページ共通） */
(function () {
  var LINKS = [
    ["トップ", "/"],
    ["直問とは", "/#eigo"],
    ["解き方", "/#how"],
    ["無料の練習問題（Day 1〜10）", "/days/1/"],
    ["文法", "/grammar/"],
    ["読み物", "/articles/"],
    ["LINEでできること", "/#line"],
    ["月額プラン", "/#plan"]
  ];
  var LINE = "https://line.me/R/ti/p/@808umztb";
  var head = document.querySelector("header");
  if (!head) return;

  var css = document.createElement("style");
  css.textContent =
    ".mnb{display:inline-flex;flex-direction:column;justify-content:center;gap:5px;width:42px;height:42px;margin:0 6px 0 -8px;padding:0 9px;background:none;border:0;border-radius:10px;cursor:pointer;flex:none}" +
    ".mnb span{display:block;height:2px;border-radius:2px;background:#F5F5F5;transition:transform .2s,opacity .2s}" +
    ".mnb:focus-visible{outline:2px solid #FF6A1A;outline-offset:2px}" +
    ".mnb[aria-expanded=true] span:nth-child(1){transform:translateY(7px) rotate(45deg)}" +
    ".mnb[aria-expanded=true] span:nth-child(2){opacity:0}" +
    ".mnb[aria-expanded=true] span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}" +
    ".mnbg{position:fixed;inset:0;z-index:98;background:rgba(0,0,0,.55);opacity:0;pointer-events:none;transition:opacity .2s}" +
    ".mnp{position:fixed;top:0;left:0;bottom:0;z-index:99;width:min(82vw,320px);background:#0E0E0E;border-right:1px solid rgba(255,106,26,.45);" +
    "transform:translateX(-100%);transition:transform .25s ease;overflow-y:auto;padding:18px 0 28px;font-family:inherit}" +
    ".mn-open .mnbg{opacity:1;pointer-events:auto}.mn-open .mnp{transform:none}" +
    ".mnp .mnh{display:flex;align-items:center;justify-content:space-between;padding:0 14px 14px 20px;border-bottom:1px solid #262626}" +
    ".mnp .mnh b{font-size:20px;color:#F5F5F5}.mnp .mnh b i{font-style:normal;color:#FF6A1A}" +
    ".mnp .mnx{width:42px;height:42px;background:none;border:0;color:#BDBDBD;font-size:26px;line-height:1;cursor:pointer;border-radius:10px}" +
    ".mnp .mnx:focus-visible{outline:2px solid #FF6A1A}" +
    ".mnp ul{list-style:none;margin:8px 0 0;padding:0}" +
    ".mnp li a{display:block;padding:14px 20px;color:#F5F5F5;text-decoration:none;font-size:16px;font-weight:700;border-left:3px solid transparent}" +
    ".mnp li a:hover,.mnp li a:focus-visible{background:#181818;outline:0}" +
    ".mnp li a[aria-current=page]{border-left-color:#FF6A1A;color:#FF6A1A}" +
    ".mnp .mnl{display:block;margin:18px 20px 0;padding:12px;border-radius:999px;background:#06C755;color:#fff;text-align:center;font-weight:700;text-decoration:none;font-size:15px}" +
    "html.mn-open,html.mn-open body{overflow:hidden}" +
    "@media (min-width:860px){.mnb,.mnbg,.mnp{display:none}}" +
    "@media (prefers-reduced-motion:reduce){.mnb span,.mnbg,.mnp{transition:none}}";
  document.head.appendChild(css);

  var btn = document.createElement("button");
  btn.className = "mnb";
  btn.type = "button";
  btn.setAttribute("aria-label", "メニューを開く");
  btn.setAttribute("aria-expanded", "false");
  btn.setAttribute("aria-controls", "mnp");
  btn.innerHTML = "<span></span><span></span><span></span>";

  var here = location.pathname;
  var items = LINKS.map(function (l) {
    var cur = l[1].indexOf("#") < 0 && (l[1] === "/" ? here === "/" || here === "/index.html" : here.indexOf(l[1].replace(/1\/$/, "")) === 0);
    return '<li><a href="' + l[1] + '"' + (cur ? ' aria-current="page"' : "") + ">" + l[0] + "</a></li>";
  }).join("");

  var bg = document.createElement("div");
  bg.className = "mnbg";
  var panel = document.createElement("nav");
  panel.className = "mnp";
  panel.id = "mnp";
  panel.setAttribute("aria-label", "サイトのメニュー");
  panel.innerHTML = '<div class="mnh"><b>直問<i>！</i></b><button class="mnx" type="button" aria-label="メニューを閉じる">×</button></div>' +
    "<ul>" + items + '</ul><a class="mnl" href="' + LINE + '">公式LINEを友だち追加</a>';
  panel.inert = true;

  var box = head.querySelector(".in") || head;
  box.insertBefore(btn, box.firstChild);
  // ロゴと三本線を左にまとめる
  var logo = btn.nextElementSibling;
  if (logo) {
    var wrap = document.createElement("div");
    wrap.style.cssText = "display:flex;align-items:center;min-width:0";
    box.insertBefore(wrap, btn);
    wrap.appendChild(btn);
    wrap.appendChild(logo);
  }
  document.body.appendChild(bg);
  document.body.appendChild(panel);

  var root = document.documentElement;
  function open() {
    root.classList.add("mn-open");
    panel.inert = false;
    btn.setAttribute("aria-expanded", "true");
    btn.setAttribute("aria-label", "メニューを閉じる");
    panel.querySelector(".mnx").focus();
  }
  function close(back) {
    if (!root.classList.contains("mn-open")) return;
    root.classList.remove("mn-open");
    panel.inert = true;
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-label", "メニューを開く");
    if (back) btn.focus();
  }
  btn.addEventListener("click", function () { root.classList.contains("mn-open") ? close(true) : open(); });
  bg.addEventListener("click", function () { close(true); });
  panel.querySelector(".mnx").addEventListener("click", function () { close(true); });
  panel.addEventListener("click", function (e) { if (e.target.closest("a")) close(false); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(true); });
})();
