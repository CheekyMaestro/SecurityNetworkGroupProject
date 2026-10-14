/* Brankas saya: stat tile + tabel paket */
App.page("buyer", async function () {
  var res = await Promise.all([api.get("/packages"), api.get("/claims").catch(function () { return { items: [] }; })]);
  var items = res[0].items, claimByPkg = {};
  res[1].items.forEach(function (c) { claimByPkg[c.package_id] = c; });

  document.getElementById("stat-packages").textContent = items.length;
  document.getElementById("stat-docs").textContent = items.reduce(function (s, p) { return s + p.document_count; }, 0);
  document.getElementById("stat-size").textContent = App.fmtBytes(items.reduce(function (s, p) { return s + p.total_size_bytes; }, 0));

  var box = document.getElementById("packages");
  if (!items.length) {
    box.innerHTML = document.getElementById("tpl-empty").innerHTML;
    App.icons(box);
    return;
  }
  var e = App.esc;
  box.innerHTML = '<table class="table table-click"><thead><tr>' +
    "<th>Barang</th><th>No. pesanan</th><th>Toko</th><th>Disimpan</th><th class=\"num\">Dokumen</th><th>Klaim</th><th></th>" +
    "</tr></thead><tbody>" + items.map(function (p) {
      var claim = claimByPkg[p.id];
      return '<tr data-href="/paket/' + p.id + '">' +
        '<td><div class="row-12">' + App.thumb() + '<div class="grow"><div class="truncate">' + e(p.item_name) + '</div>' +
        '<div class="mono muted">' + App.fmtBytes(p.total_size_bytes) + "</div></div></div></td>" +
        '<td class="mono">' + e(p.order_no || "–") + "</td>" +
        "<td>" + e(p.store || "–") + "</td>" +
        '<td class="muted">' + App.fmtDate(p.created_at) + "</td>" +
        '<td class="num mono">' + (p.document_count || '<span class="muted">0</span>') + "</td>" +
        "<td>" + (claim ? App.badge(claim.status) : '<span class="muted">–</span>') + "</td>" +
        '<td class="num"><a class="btn" href="/paket/' + p.id + '">Lihat<i data-lucide="arrow-right"></i></a></td></tr>';
    }).join("") + "</tbody></table>";
  box.querySelectorAll("tr[data-href]").forEach(function (tr) {
    tr.addEventListener("click", function (ev) { if (!ev.target.closest("a")) location.href = tr.dataset.href; });
  });
  App.icons(box);
});
