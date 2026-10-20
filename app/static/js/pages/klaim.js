/* Ajukan klaim: pilih toko, tulis keluhan, ringkasan file yang dibuka toko → POST /claims */
App.page("buyer", async function () {
  var e = App.esc;
  var res = await Promise.all([api.get("/packages/" + window.PACKAGE_ID), api.get("/stores")]);
  var pkg = res[0], stores = res[1].items;
  if (pkg.claim) { location.replace("/paket/" + pkg.id); return; }

  document.title = "Klaim " + pkg.item_name + " · Awan";
  document.getElementById("pkg-line").innerHTML = e(pkg.item_name) + (pkg.order_no ? ' · <span class="mono">' + e(pkg.order_no) + "</span>" : "");

  var form = document.getElementById("claim-form");
  var sel = form.store_user_id;
  var guess = stores.filter(function (s) { return s.store_name.toLowerCase() === (pkg.store || "").toLowerCase(); })[0];
  sel.innerHTML = '<option value="">Pilih toko</option>' + stores.map(function (s) {
    return '<option value="' + s.id + '"' + (guess && guess.id === s.id ? " selected" : "") + ">" + e(s.store_name) + "</option>";
  }).join("");
  sel.disabled = false;

  var btn = document.getElementById("submit");
  function syncLabel() {
    var s = stores.filter(function (x) { return x.id === +sel.value; })[0];
    btn.innerHTML = '<i data-lucide="send"></i>' + (s ? "Kirim ke " + e(s.store_name) : "Kirim");
    App.icons(btn);
  }
  sel.addEventListener("change", syncLabel);
  syncLabel();

  var shared = pkg.files.filter(function (f) { return f.category !== "id_card"; });
  document.getElementById("files-count").textContent = shared.length + " file";
  document.getElementById("files").innerHTML = shared.length ? shared.map(function (f) {
    return '<div class="mini-card">' + App.fileIcon(f) + '<div class="file-meta"><div class="name" title="' + e(f.name) + '">' + e(f.name) +
      '</div><div class="mono">' + App.fmtBytes(f.size_bytes) + "</div></div></div>";
  }).join("") : '<p class="desc">Paket ini belum punya file. Toko hanya akan membaca keluhanmu.</p>';
  App.icons(document.getElementById("files"));

  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    App.clearErrors(form);
    var bad = false;
    if (!sel.value) { App.fieldError(sel, "Pilih toko tujuan dulu."); bad = true; }
    if (!form.message.value.trim()) { App.fieldError(form.message, "Tulis keluhanmu dulu."); bad = true; }
    if (bad) return;
    var storeName = sel.options[sel.selectedIndex].text;
    App.setBusy(btn, true, "Mengirim…");
    try {
      await api.post("/claims", { package_id: pkg.id, store_user_id: +sel.value, message: form.message.value.trim() });
      App.toastNext("Klaim terkirim ke " + storeName);
      location.href = "/paket/" + pkg.id;
    } catch (err) {
      App.setBusy(btn, false);
      App.formAlert(document.getElementById("form-alert"), err.detail);
    }
  });
});
