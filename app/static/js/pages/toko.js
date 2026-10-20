/* Klaim masuk (toko): chip filter status + grid kartu */
App.page("store", async function () {
  var e = App.esc;
  var items = (await api.get("/claims")).items;
  var filter = "semua";
  var ORDER = ["semua", "diajukan", "ditinjau", "diterima", "ditolak"];

  function count(s) { return s === "semua" ? items.length : items.filter(function (c) { return c.status === s; }).length; }

  function renderChips() {
    var box = document.getElementById("filters");
    box.innerHTML = ORDER.map(function (s) {
      var label = s === "semua" ? "Semua" : App.STATUS[s].label;
      return '<button type="button" role="tab" class="chip' + (s === filter ? " is-active" : "") + '" aria-selected="' + (s === filter) + '" data-filter="' + s + '">' +
        label + '<span class="count">' + count(s) + "</span></button>";
    }).join("");
  }

  function renderCards() {
    var box = document.getElementById("claims");
    var list = items.filter(function (c) { return filter === "semua" || c.status === filter; });
    if (!items.length) {
      box.innerHTML = '<div class="panel">' + App.emptyState("Belum ada klaim masuk",
        "Kalau pembeli mengajukan klaim ke tokomu, kartunya muncul di sini lengkap dengan video unboxing.") + "</div>";
      return;
    }
    if (!list.length) {
      box.innerHTML = '<div class="panel">' + App.emptyState("Tidak ada klaim " + App.STATUS[filter].label.toLowerCase(),
        "Coba pilih status lain.", '<button type="button" class="btn" data-filter="semua">Lihat semua</button>') + "</div>";
      return;
    }
    box.innerHTML = '<div class="card-grid">' + list.map(function (c) {
      return '<article class="card">' + App.thumb(true) +
        '<div class="card-body"><div class="row"><span class="grow truncate" title="' + e(c.item_name) + '">' + e(c.item_name) + "</span>" + App.badge(c.status) + "</div>" +
        '<div class="mono muted truncate">' + e(c.order_no || "–") + "</div>" +
        '<div class="row muted" style="margin-top:4px"><i data-lucide="user-round"></i><span class="truncate">' + e(c.buyer_name) + "</span></div></div>" +
        '<div class="card-footer"><span class="mono muted">' + App.fmtDate(c.created_at) + "</span>" +
        '<a class="btn' + (c.status === "diajukan" ? " btn-primary" : "") + '" href="/toko/klaim/' + c.id + '">Tinjau<i data-lucide="arrow-right"></i></a></div></article>';
    }).join("") + "</div>";
  }

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("[data-filter]");
    if (!b) return;
    filter = b.dataset.filter;
    renderChips();
    renderCards();
    App.icons();
  });
  renderChips();
  renderCards();
});
