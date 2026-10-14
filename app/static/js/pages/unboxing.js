/* Simpan unboxing: POST /packages → POST /files (video) → POST /files (tiap dokumen), progress per file. */
(function () {
  "use strict";
  var MB = 1024 * 1024;
  var VIDEO_EXT = /\.(mp4|mkv|mov)$/i;
  var DOC_EXT = /\.(pdf|docx?|xlsx?)$/i;

  var video = null;          // {file, uploaded, el}
  var docs = [];             // [{key, file, uploaded, el}]
  var packageId = null;      // disimpan supaya "coba lagi" tidak membuat paket dobel
  var uploading = false;
  var seq = 0;

  function $(id) { return document.getElementById(id); }

  function setProgress(bar, frac, cls) {
    bar.hidden = false;
    bar.className = "progress" + (cls ? " " + cls : "");
    bar.firstElementChild.style.width = Math.round(frac * 100) + "%";
  }

  function wireDrop(zone, input, onFiles) {
    zone.addEventListener("click", function () { if (!uploading) input.click(); });
    zone.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
    ["dragenter", "dragover"].forEach(function (t) {
      zone.addEventListener(t, function (e) { e.preventDefault(); zone.classList.add("is-over"); });
    });
    ["dragleave", "drop"].forEach(function (t) {
      zone.addEventListener(t, function (e) { e.preventDefault(); zone.classList.remove("is-over"); });
    });
    zone.addEventListener("drop", function (e) { if (!uploading) onFiles(Array.from(e.dataTransfer.files)); });
    input.addEventListener("change", function () { onFiles(Array.from(input.files)); input.value = ""; });
  }

  function videoError(msg) {
    var zone = $("video-drop");
    var old = $("video-panel").querySelector(".field-error");
    if (old) old.remove();
    zone.classList.toggle("is-invalid", !!msg);
    if (msg) {
      var el = document.createElement("div");
      el.className = "field-error";
      el.textContent = msg;
      $("video-panel").querySelector(".panel-body").appendChild(el);
    }
  }

  function setVideo(files) {
    var f = files[0];
    if (!f) return;
    if (!VIDEO_EXT.test(f.name)) return videoError("Format video harus MP4, MKV, atau MOV.");
    if (f.size > 100 * MB) return videoError("Video " + App.fmtBytes(f.size) + " melebihi batas 100 MB.");
    videoError(null);
    var prev = $("video-preview");
    if (prev.src) URL.revokeObjectURL(prev.src);
    prev.src = URL.createObjectURL(f);
    $("video-name").textContent = f.name;
    $("video-size").textContent = App.fmtBytes(f.size);
    $("video-progress").hidden = true;
    $("video-drop").hidden = true;
    $("video-chosen").hidden = false;
    video = { file: f, uploaded: false };
    packageId = null;
  }

  function renderDocs() {
    var list = $("docs-list");
    $("docs-empty").hidden = docs.length > 0;
    list.innerHTML = docs.map(function (d) {
      var f = { id: d.key, name: d.file.name, size_bytes: d.file.size, mime_type: d.file.type, category: "document" };
      var extra = '<div class="progress" data-progress hidden><span></span></div>' +
        (d.error ? '<div class="field-error">' + App.esc(d.error) + "</div>" : "");
      var actions = d.uploaded ? '<span class="badge badge-ok">Terenkripsi</span>'
        : '<button type="button" class="btn btn-ghost btn-icon" data-remove="' + d.key + '" aria-label="Hapus dari daftar"><i data-lucide="x"></i></button>';
      return App.fileRow(f, actions, extra);
    }).join("");
    docs.forEach(function (d) { d.el = list.querySelector('[data-file-id="' + d.key + '"]'); });
    App.icons(list);
  }

  function addDocs(files) {
    var rejected = [];
    files.forEach(function (f) {
      if (!DOC_EXT.test(f.name)) rejected.push(f.name + ": format tidak didukung");
      else if (f.size > 20 * MB) rejected.push(f.name + ": melebihi 20 MB");
      else docs.push({ key: "d" + (++seq), file: f, uploaded: false });
    });
    renderDocs();
    if (rejected.length) App.toast("Tidak ditambahkan — " + rejected.join("; "), "error");
  }

  function setUploading(on) {
    uploading = on;
    $("submit").disabled = on;
    $("video-replace").disabled = on;
    $("docs-add").disabled = on;
    $("cancel").setAttribute("aria-disabled", String(on));
    document.querySelectorAll("#unboxing-form input").forEach(function (i) { i.readOnly = on; });
    document.querySelectorAll("[data-remove]").forEach(function (b) { b.disabled = on; });
  }

  function beforeUnload(e) {
    if (!uploading) return;
    e.preventDefault();
    e.returnValue = "";
  }

  async function uploadOne(file, category, bar) {
    var fd = new FormData();
    fd.append("file", file);
    fd.append("category", category);
    fd.append("package_id", String(packageId));
    setProgress(bar, 0);
    try {
      var res = await api.upload("/files", fd, function (p) { setProgress(bar, Math.min(p, 0.99)); });
      setProgress(bar, 1, "is-done");
      return res;
    } catch (err) {
      setProgress(bar, 1, "is-error");
      throw err;
    }
  }

  async function submit(e) {
    e.preventDefault();
    if (uploading) return;
    var form = $("unboxing-form");
    App.clearErrors(form);
    var bad = false;
    if (!video) { videoError("Pilih video unboxing dulu."); bad = true; }
    if (!form.item_name.value.trim()) { App.fieldError(form.item_name, "Nama barang wajib diisi."); bad = true; }
    if (!form.store.value.trim()) { App.fieldError(form.store, "Nama toko wajib diisi."); bad = true; }
    if (bad) {
      App.formAlert($("form-alert"), "Lengkapi yang ditandai merah dulu.");
      return;
    }

    setUploading(true);
    var btn = $("submit");
    App.setBusy(btn, true, "Mengenkripsi…");
    var status = $("upload-status");
    var pending = (video.uploaded ? 0 : 1) + docs.filter(function (d) { return !d.uploaded; }).length;
    var done = 0;
    var step = function () { status.textContent = "Mengunggah " + Math.min(done + 1, pending) + " dari " + pending + " file…"; };

    try {
      if (!packageId) {
        status.textContent = "Membuat paket…";
        var pkg = await api.post("/packages", {
          item_name: form.item_name.value.trim(), store: form.store.value.trim(), order_no: form.order_no.value.trim()
        });
        packageId = pkg.id;
      }
      if (!video.uploaded) {
        step();
        await uploadOne(video.file, "video", $("video-progress"));
        video.uploaded = true; done++;
      }
      for (var i = 0; i < docs.length; i++) {
        var d = docs[i];
        if (d.uploaded) continue;
        step();
        d.error = null;
        try {
          await uploadOne(d.file, "document", d.el.querySelector("[data-progress]"));
          d.uploaded = true; done++;
        } catch (err) {
          d.error = err.detail;
          throw err;
        }
      }
      uploading = false;
      App.toastNext("Tersimpan dan terenkripsi");
      location.href = "/paket/" + packageId;
    } catch (err) {
      setUploading(false);
      App.setBusy(btn, false);
      btn.innerHTML = '<i data-lucide="rotate-cw"></i>Coba lagi';
      App.icons(btn);
      status.textContent = "";
      App.formAlert($("form-alert"), (packageId ? "Sebagian file belum tersimpan: " : "") + err.detail);
      var errored = docs.some(function (x) { return x.error; });
      if (errored) {
        // Tampilkan ulang daftar dengan pesan error per file, tetap pertahankan bar progress yang sudah selesai
        renderDocs();
        docs.forEach(function (x) { if (x.uploaded) setProgress(x.el.querySelector("[data-progress]"), 1, "is-done"); });
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  App.page("buyer", function () {
    wireDrop($("video-drop"), $("video-input"), setVideo);
    wireDrop($("docs-drop"), $("docs-input"), addDocs);
    $("video-replace").addEventListener("click", function () { $("video-input").click(); });
    $("docs-add").addEventListener("click", function () { $("docs-input").click(); });
    $("docs-list").addEventListener("click", function (e) {
      var b = e.target.closest("[data-remove]");
      if (!b || uploading) return;
      docs = docs.filter(function (d) { return d.key !== b.dataset.remove; });
      renderDocs();
    });
    $("cancel").addEventListener("click", function (e) { if (uploading) e.preventDefault(); });
    $("unboxing-form").addEventListener("submit", submit);
    window.addEventListener("beforeunload", beforeUnload);
    renderDocs();
  });
})();
