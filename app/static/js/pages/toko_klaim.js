/* Tinjau klaim (toko): video, dokumen, pembeli tanpa data sensitif, keputusan, percakapan */
(function () {
  "use strict";
  var e = App.esc, claim = null;
  function $(id) { return document.getElementById(id); }

  function render() {
    var c = claim;
    document.title = "Klaim " + c.package.item_name + " · Awan";
    $("title").textContent = c.package.item_name;
    $("meta").innerHTML = App.badge(c.status) + '<span class="mono">' + e(c.package.order_no || "–") + '</span><span class="dot"></span>' +
      "<span>Diajukan " + App.fmtDateTime(c.created_at) + "</span>";

    var video = c.files.filter(function (f) { return f.category === "video"; })[0];
    $("player").innerHTML = video
      ? '<div class="player"><video controls preload="metadata" playsinline src="' + e(api.fileUrl(video, "aes")) + '"></video></div>' +
        App.fileRow(video, '<a class="btn" href="' + e(api.fileUrl(video, "aes")) + '" download="' + e(video.name) + '"><i data-lucide="download"></i>Unduh</a>')
      : App.thumb(true) + '<div class="file-row"><span class="muted">Pembeli tidak menyertakan video.</span></div>';

    var docs = c.files.filter(function (f) { return f.category === "document"; });
    $("docs").innerHTML = docs.length ? docs.map(function (f) {
      return App.fileRow(f, '<a class="btn" href="' + e(api.fileUrl(f, "aes")) + '" download="' + e(f.name) + '"><i data-lucide="download"></i>Unduh</a>');
    }).join("") : '<div class="file-row"><span class="muted">Tidak ada dokumen.</span></div>';

    $("buyer").innerHTML =
      '<div class="stack-12"><div class="row-12"><span class="avatar" style="cursor:default">' + e(App.initials(c.buyer.name)) + '</span>' +
        '<div class="grow"><div>' + e(c.buyer.name) + "</div>" +
        (c.buyer.ktp_verified
          ? '<span class="badge badge-ok"><i data-lucide="badge-check" style="width:11px;height:11px"></i>KTP terverifikasi</span>'
          : '<span class="badge badge-warn">KTP belum diverifikasi</span>') + "</div></div>" +
      '<div><span class="label">Keluhan</span><p class="quote" style="margin:6px 0 0">' + e(c.message) + "</p></div>" +
      '<p class="desc" style="display:flex;gap:6px"><i data-lucide="lock" style="margin-top:2px"></i>NIK, nomor HP, dan rekening pembeli tidak dibagikan ke toko.</p></div>';

    $("thread").innerHTML = c.replies.length ? '<div class="thread">' + c.replies.map(function (r) {
      var mine = r.author_role === "store";
      return '<div class="msg' + (mine ? " is-store is-mine" : "") + '"><span class="avatar">' + e(App.initials(r.author_name)) + "</span>" +
        '<div class="msg-bubble"><div class="msg-meta"><span>' + e(r.author_name) + '</span><span class="mono muted">' + App.fmtDateTime(r.created_at) + "</span></div>" +
        '<div class="msg-body">' + e(r.body) + "</div></div></div>";
    }).join("") + "</div>" : '<p class="desc">Belum ada pesan. Balasan dari keputusanmu juga muncul di sini.</p>';

    var pre = document.querySelector('input[name="decision"][value="' + (c.status === "diterima" || c.status === "ditolak" ? c.status : "") + '"]');
    if (pre) pre.checked = true;
    App.icons();
  }

  App.page("store", async function () {
    claim = await api.get("/claims/" + window.CLAIM_ID);
    render();

    $("decision-form").addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var form = ev.target;
      App.clearErrors(form);
      var picked = form.querySelector('input[name="decision"]:checked');
      var reply = form.reply.value.trim();
      if (!picked) return App.formAlert($("form-alert"), "Pilih keputusan dulu.");
      if (picked.value !== "diterima" && !reply) {
        App.fieldError(form.reply, picked.value === "ditolak" ? "Tulis alasan penolakan untuk pembeli." : "Tulis bukti apa yang perlu ditambahkan.");
        return form.reply.focus();
      }
      var btn = $("decision-submit");
      App.setBusy(btn, true, "Menyimpan…");
      try {
        claim = await api.patch("/claims/" + claim.id, { status: picked.value, reply: reply });
        form.reply.value = "";
        render();
        App.toast("Keputusan tersimpan · " + App.STATUS[claim.status].label);
      } catch (err) {
        App.formAlert($("form-alert"), err.detail);
      }
      App.setBusy(btn, false);
    });

    $("reply-form").addEventListener("submit", async function (ev) {
      ev.preventDefault();
      var input = $("reply-body");
      App.fieldError(input, null);
      if (!input.value.trim()) return App.fieldError(input, "Pesan masih kosong.");
      var btn = $("reply-submit");
      App.setBusy(btn, true, "Mengirim…");
      try {
        await api.post("/claims/" + claim.id + "/replies", { body: input.value.trim() });
        claim = await api.get("/claims/" + claim.id);
        input.value = "";
        render();
        App.toast("Pesan terkirim");
      } catch (err) {
        App.fieldError(input, err.detail);
      }
      App.setBusy(btn, false);
    });
  });
})();
