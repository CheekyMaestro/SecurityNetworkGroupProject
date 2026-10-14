/* Detail paket: video, dokumen, klaim, mode demo algoritma */
(function () {
  "use strict";
  var e = App.esc;
  var pkg = null, alg = "aes";
  var STEPS = ["diajukan", "ditinjau", "keputusan"];

  function $(id) { return document.getElementById(id); }

  function renderHeader() {
    document.title = pkg.item_name + " · Awan";
    $("pkg-title").textContent = pkg.item_name;
    $("pkg-meta").innerHTML =
      (pkg.order_no ? '<span class="mono">' + e(pkg.order_no) + '</span><span class="dot"></span>' : "") +
      "<span>" + e(pkg.store || "Toko tidak diisi") + '</span><span class="dot"></span>' +
      "<span>Disimpan " + App.fmtDateTime(pkg.created_at) + "</span>";
  }

  function downloadBtn(f) {
    return '<a class="btn" data-download="' + f.id + '" href="' + e(api.fileUrl(f, alg)) + '" download="' + e(f.name) + '"><i data-lucide="download"></i>Unduh</a>';
  }

  function renderMedia() {
    var video = pkg.files.filter(function (f) { return f.category === "video"; })[0];
    if (video) {
      $("player").innerHTML = '<div class="player"><video controls preload="metadata" playsinline src="' + e(api.fileUrl(video, alg)) + '"></video></div>';
      $("video-row").innerHTML = App.fileRow(video, downloadBtn(video));
    } else {
      $("player").innerHTML = App.thumb(true);
      $("video-row").innerHTML = '<div class="file-row"><span class="muted">Video paket ini sudah dihapus.</span></div>';
    }
    var docs = pkg.files.filter(function (f) { return f.category === "document"; });
    $("docs").innerHTML = docs.length
      ? docs.map(function (f) {
          return App.fileRow(f, downloadBtn(f) +
            '<button type="button" class="btn btn-danger" data-delete="' + f.id + '"><i data-lucide="trash-2"></i>Hapus</button>');
        }).join("")
      : '<div class="file-row"><span class="muted">Belum ada dokumen untuk paket ini.</span></div>';
    App.icons($("video-panel"));
    App.icons($("docs"));
  }

  function setAlg(next) {
    alg = next;
    document.querySelectorAll("#alg-switch [data-alg]").forEach(function (b) {
      var on = b.dataset.alg === alg;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-checked", String(on));
    });
    $("alg-hint").textContent = "/files/{id}/download?alg=" + alg;
    var v = document.querySelector("#player video");
    var video = pkg.files.filter(function (f) { return f.category === "video"; })[0];
    if (v && video) { v.src = api.fileUrl(video, alg); v.load(); }
    document.querySelectorAll("[data-download]").forEach(function (a) {
      var f = pkg.files.filter(function (x) { return x.id === +a.dataset.download; })[0];
      if (f) a.href = api.fileUrl(f, alg);
    });
    App.toast("Sekarang memakai ciphertext " + App.ALG_LABEL[alg], "info");
  }

  async function onDelete(id) {
    var f = pkg.files.filter(function (x) { return x.id === id; })[0];
    var ok = await App.confirm({
      title: "Hapus dokumen ini?",
      body: "“" + f.name + "” dan ketiga ciphertext-nya (AES, RC4, DES) akan dihapus permanen.",
      confirm: "Hapus", danger: true
    });
    if (!ok) return;
    try {
      await api.del("/files/" + id);
      pkg.files = pkg.files.filter(function (x) { return x.id !== id; });
      renderMedia();
      App.toast("Dokumen dihapus");
    } catch (err) { App.toast(err.detail, "error"); }
  }

  function timeline(status) {
    var idx = status === "diajukan" ? 0 : status === "ditinjau" ? 1 : 2;
    return '<div class="timeline">' + STEPS.map(function (s, i) {
      var cls = i < idx ? "is-done" : i === idx ? "is-current" : "";
      var label = s === "keputusan" ? (status === "diterima" ? "Diterima" : status === "ditolak" ? "Ditolak" : "Keputusan") : App.STATUS[s].label;
      if (i === 2 && status === "diterima") cls = "is-ok";
      if (i === 2 && status === "ditolak") cls = "is-bad";
      if (i === idx && i < 2) cls = "is-current";
      if (i < idx) cls = "is-done";
      return '<div class="tl-step ' + cls + '"><span class="tl-dot"></span><span class="label">' + label + "</span></div>";
    }).join("") + "</div>";
  }

  function thread(replies, meRole) {
    if (!replies.length) return '<p class="desc">Belum ada balasan dari toko.</p>';
    return '<div class="thread">' + replies.map(function (r) {
      var mine = r.author_role === meRole;
      return '<div class="msg' + (r.author_role === "store" ? " is-store" : "") + (mine ? " is-mine" : "") + '">' +
        '<span class="avatar">' + e(App.initials(r.author_name)) + "</span>" +
        '<div class="msg-bubble"><div class="msg-meta"><span>' + e(r.author_name) + '</span><span class="mono muted">' + App.fmtDateTime(r.created_at) + "</span></div>" +
        '<div class="msg-body">' + e(r.body) + "</div></div></div>";
    }).join("") + "</div>";
  }

  async function renderClaim() {
    var box = $("claim");
    if (!pkg.claim) {
      box.innerHTML = '<div class="stack-12"><p class="desc">Barang rusak, kurang, atau tidak sesuai? Ajukan klaim ke toko. ' +
        "Toko hanya bisa membuka video dan dokumen paket ini, bukan data pribadimu.</p>" +
        '<a class="btn btn-primary btn-lg" href="/paket/' + pkg.id + '/klaim"><i data-lucide="send"></i>Ajukan klaim</a></div>';
      App.icons(box);
      return;
    }
    var c = await api.get("/claims/" + pkg.claim.id);
    box.innerHTML =
      '<div class="stack-16">' +
        '<div class="row"><span class="grow">Klaim ke <strong style="font-weight:600">' + e(c.store.store_name) + "</strong></span>" + App.badge(c.status) + "</div>" +
        timeline(c.status) +
        '<p class="desc">' + e(App.STATUS[c.status].desc) + " · diajukan " + App.fmtDate(c.created_at) + "</p>" +
        '<div><span class="label">Keluhanmu</span><p class="quote" style="margin:6px 0 0">' + e(c.message) + "</p></div>" +
        '<div class="divider"></div>' +
        '<div><span class="label" style="display:block;margin-bottom:8px">Percakapan</span>' + thread(c.replies, "buyer") + "</div>" +
        '<form class="reply-box" id="reply-form" novalidate>' +
          '<textarea class="textarea" name="body" placeholder="Tulis balasan untuk toko…" maxlength="2000"></textarea>' +
          '<div class="row" style="justify-content:flex-end"><button class="btn btn-primary" type="submit" id="reply-submit"><i data-lucide="send"></i>Kirim balasan</button></div>' +
        "</form>" +
      "</div>";
    App.icons(box);
    $("reply-form").addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var form = ev.target;
      App.clearErrors(form);
      var body = form.body.value.trim();
      if (!body) return App.fieldError(form.body, "Balasan masih kosong.");
      var btn = $("reply-submit");
      App.setBusy(btn, true, "Mengirim…");
      try {
        await api.post("/claims/" + c.id + "/replies", { body: body });
        App.toast("Balasan terkirim");
        await renderClaim();
      } catch (err) {
        App.setBusy(btn, false);
        App.fieldError(form.body, err.detail);
      }
    });
  }

  App.page("buyer", async function () {
    pkg = await api.get("/packages/" + window.PACKAGE_ID);
    renderHeader();
    renderMedia();
    $("docs").addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-delete]");
      if (b) onDelete(+b.dataset.delete);
    });
    $("alg-switch").addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-alg]");
      if (b && b.dataset.alg !== alg) setAlg(b.dataset.alg);
    });
    await renderClaim();
  });
})();
