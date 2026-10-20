/* Statistik enkripsi: GET /stats → Chart.js. Warna per algoritma tetap (AES/RC4/DES), tidak mengikuti urutan. */
App.page("buyer", async function () {
  var stats = await api.get("/stats");
  if (api.mock) document.getElementById("sample-badge").hidden = false;

  var css = getComputedStyle(document.documentElement);
  var tok = function (n) { return css.getPropertyValue(n).trim(); };
  var ALGS = ["aes", "rc4", "des"];
  var COLOR = { aes: tok("--brand-600"), rc4: tok("--brand-400"), des: tok("--brand-200") };
  var EDGE = { aes: tok("--brand-600"), rc4: tok("--brand-500"), des: tok("--brand-400") };
  var CAT = { video: "Video", document: "Dokumen", id_card: "Foto KTP" };
  var byAlg = {};
  stats.per_algorithm.forEach(function (r) { byAlg[r.algorithm] = r; });
  var mb = function (b) { return b / (1024 * 1024); };

  Chart.defaults.font.family = tok("--font-ui");
  Chart.defaults.font.size = 12;
  Chart.defaults.color = tok("--muted");

  // Label nilai di atas batang (DES berwarna terang, jadi angka selalu terlihat)
  var valueLabels = {
    id: "valueLabels",
    afterDatasetsDraw: function (chart, args, opts) {
      var ctx = chart.ctx;
      ctx.save();
      ctx.font = "500 11px " + tok("--font-mono");
      ctx.fillStyle = tok("--ink-2");
      ctx.textAlign = "center";
      chart.data.datasets.forEach(function (ds, i) {
        chart.getDatasetMeta(i).data.forEach(function (bar, j) {
          var v = ds.data[j];
          if (v == null) return;
          ctx.fillText(opts.format(v), bar.x, bar.y - 6);
        });
      });
      ctx.restore();
    }
  };

  function barChart(id, labels, datasets, unit, digits) {
    document.getElementById("sk-" + id.replace("chart-", "")).remove();
    return new Chart(document.getElementById(id), {
      type: "bar",
      data: { labels: labels, datasets: datasets.map(function (d) {
        return Object.assign({ borderWidth: 1, borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: "bottom", maxBarThickness: 36 }, d);
      }) },
      plugins: [valueLabels],
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 300 },
        layout: { padding: { top: 20 } },
        datasets: { bar: { categoryPercentage: 0.7, barPercentage: 0.9 } },
        plugins: {
          legend: { display: false },
          valueLabels: { format: function (v) { return App.fmtNum(v, digits); } },
          tooltip: {
            backgroundColor: tok("--ink"), padding: 8, cornerRadius: 6, boxPadding: 4,
            callbacks: { label: function (c) { return " " + c.dataset.label + ": " + App.fmtNum(c.parsed.y, digits) + " " + unit; } }
          }
        },
        scales: {
          x: { grid: { display: false }, border: { color: tok("--border") } },
          y: { beginAtZero: true, grid: { color: tok("--surface-hover") }, border: { display: false },
               ticks: { callback: function (v) { return App.fmtNum(v) + " " + unit; } } }
        }
      }
    });
  }

  function algDataset(a, data) {
    return { label: App.ALG_LABEL[a], data: data, backgroundColor: COLOR[a], borderColor: EDGE[a] };
  }

  barChart("chart-time", ["Enkripsi", "Dekripsi"], ALGS.filter(function (a) { return byAlg[a]; }).map(function (a) {
    return algDataset(a, [byAlg[a].avg_enc_ms_per_mb, byAlg[a].avg_dec_ms_per_mb]);
  }), "ms", 1);

  var present = ALGS.filter(function (a) { return byAlg[a]; });
  barChart("chart-size", ["Ciphertext"], present.map(function (a) {
    return algDataset(a, [mb(byAlg[a].total_cipher_bytes)]);
  }), "MB", 1);

  var cats = [];
  stats.per_category.forEach(function (r) { if (cats.indexOf(r.category) < 0) cats.push(r.category); });
  barChart("chart-cat", cats.map(function (c) { return CAT[c] || c; }), ALGS.map(function (a) {
    return algDataset(a, cats.map(function (c) {
      var r = stats.per_category.filter(function (x) { return x.category === c && x.algorithm === a; })[0];
      return r ? r.avg_enc_ms_per_mb : null;
    }));
  }).filter(function (d) { return d.data.some(function (v) { return v != null; }); }), "ms", 1);

  document.getElementById("table").innerHTML = '<table class="table"><thead><tr><th>Algoritma</th>' +
    '<th class="num">Enkripsi (ms/MB)</th><th class="num">Dekripsi (ms/MB)</th><th class="num">Total ciphertext</th></tr></thead><tbody>' +
    present.map(function (a) {
      var r = byAlg[a];
      return '<tr><td><span class="row"><i style="width:10px;height:10px;border-radius:2px;display:inline-block;background:' + COLOR[a] + ";border:1px solid " + EDGE[a] + '"></i>' + App.ALG_LABEL[a] + "</span></td>" +
        '<td class="num mono">' + App.fmtNum(r.avg_enc_ms_per_mb, 2) + '</td><td class="num mono">' + App.fmtNum(r.avg_dec_ms_per_mb, 2) + "</td>" +
        '<td class="num mono">' + App.fmtBytes(r.total_cipher_bytes) + ' <span class="muted">(' + r.total_cipher_bytes.toLocaleString("id-ID") + " B)</span></td></tr>";
    }).join("") + "</tbody></table>";
});
