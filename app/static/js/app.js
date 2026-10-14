/* Awan — utilitas bersama halaman: toast, dialog, guard login, menu akun, banner mock, format. */
(function () {
  "use strict";

  var STATUS = {
    diajukan: { label: "Diajukan", desc: "Menunggu toko membuka klaim" },
    ditinjau: { label: "Ditinjau", desc: "Toko sedang memeriksa bukti" },
    diterima: { label: "Diterima", desc: "Toko menerima klaimmu" },
    ditolak: { label: "Ditolak", desc: "Toko menolak klaim ini" }
  };
  var ALG_LABEL = { aes: "AES", rc4: "RC4", des: "DES" };
  var HOME = { buyer: "/brankas", store: "/toko" };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function icons(root) {
    if (!window.lucide) return;
    window.lucide.createIcons({ attrs: { "stroke-width": 1.5 }, root: root || document });
  }

  // ---------- format ----------
  var nf1 = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 1 });
  var nf2 = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });
  function fmtBytes(n) {
    if (n == null) return "–";
    if (n < 1024) return n + " B";
    var units = ["KB", "MB", "GB", "TB"], i = -1;
    do { n /= 1024; i++; } while (n >= 1024 && i < units.length - 1);
    return nf1.format(n) + " " + units[i];
  }
  function fmtDate(iso) {
    if (!iso) return "–";
    return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
  }
  function fmtDateTime(iso) {
    if (!iso) return "–";
    var d = new Date(iso);
    return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) + ", " +
      d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
  }
  function fmtNum(n, digits) { return (digits === 2 ? nf2 : nf1).format(n); }
  function initials(name) {
    return String(name || "?").trim().split(/\s+/).slice(0, 2).map(function (w) { return w[0]; }).join("") || "?";
  }

  // ---------- potongan HTML yang dipakai banyak halaman (cermin komponen Jinja) ----------
  function badge(status) {
    var s = STATUS[status];
    return '<span class="badge badge-' + esc(status) + '">' + esc(s ? s.label : status) + "</span>";
  }
  function thumb(large) {
    return '<span class="thumb' + (large ? " thumb-lg" : "") + '"><span class="play"><i data-lucide="play"></i></span></span>';
  }
  function fileKind(file) {
    var n = (file.name || "").toLowerCase(), m = file.mime_type || "";
    if (file.category === "video" || m.indexOf("video/") === 0) return { cls: "vid", icon: "film", label: "Video" };
    if (file.category === "id_card" || m.indexOf("image/") === 0) return { cls: "", icon: "id-card", label: "Gambar" };
    if (/\.pdf$/.test(n) || m === "application/pdf") return { cls: "pdf", icon: "file-text", label: "PDF" };
    if (/\.xlsx?$/.test(n) || m.indexOf("sheet") >= 0 || m.indexOf("excel") >= 0) return { cls: "xls", icon: "file-spreadsheet", label: "Sheet" };
    if (/\.docx?$/.test(n) || m.indexOf("word") >= 0) return { cls: "doc", icon: "file-type", label: "Dokumen" };
    return { cls: "", icon: "file", label: "File" };
  }
  function fileIcon(file) {
    var k = fileKind(file);
    return '<span class="file-icon ' + k.cls + '"><i data-lucide="' + k.icon + '"></i></span>';
  }
  /** Baris file: ikon jenis, nama, ukuran mono, dan slot aksi (HTML). */
  function fileRow(file, actionsHtml, extraHtml) {
    return '<div class="file-row" data-file-id="' + esc(file.id) + '">' + fileIcon(file) +
      '<div class="file-meta"><div class="name" title="' + esc(file.name) + '">' + esc(file.name) + "</div>" +
      '<div class="mono">' + fmtBytes(file.size_bytes) + (file.created_at ? " · " + fmtDate(file.created_at) : "") + "</div>" +
      (extraHtml || "") + "</div>" + (actionsHtml ? '<div class="row">' + actionsHtml + "</div>" : "") + "</div>";
  }
  function emptyState(title, desc, actionHtml) {
    return '<div class="empty-state"><img src="/static/img/logo.svg" alt="">' +
      "<h3>" + esc(title) + "</h3>" + (desc ? '<p class="desc">' + esc(desc) + "</p>" : "") + (actionHtml || "") + "</div>";
  }

  // ---------- toast ----------
  function toast(message, type) {
    var region = document.getElementById("toast-region");
    if (!region) { region = document.createElement("div"); region.id = "toast-region"; region.className = "toast-region"; document.body.appendChild(region); }
    var icon = type === "error" ? "circle-alert" : type === "info" ? "info" : "check";
    var el = document.createElement("div");
    el.className = "toast" + (type ? " is-" + type : "");
    el.setAttribute("role", type === "error" ? "alert" : "status");
    el.innerHTML = '<span class="toast-icon"><i data-lucide="' + icon + '"></i></span><span>' + esc(message) + "</span>";
    region.appendChild(el);
    icons(el);
    setTimeout(function () { el.classList.add("is-leaving"); setTimeout(function () { el.remove(); }, 220); }, 3000);
  }
  // Toast yang perlu tampil setelah pindah halaman (mis. "Tersimpan dan terenkripsi")
  function toastNext(message, type) {
    try { sessionStorage.setItem("awanToast", JSON.stringify({ m: message, t: type || "" })); } catch (e) { /* abaikan */ }
  }
  function flushToast() {
    var raw = null;
    try { raw = sessionStorage.getItem("awanToast"); sessionStorage.removeItem("awanToast"); } catch (e) { return; }
    if (raw) { try { var t = JSON.parse(raw); toast(t.m, t.t); } catch (e) { /* abaikan */ } }
  }

  // ---------- dialog konfirmasi ----------
  function confirmDialog(opts) {
    return new Promise(function (resolve) {
      var dlg = document.createElement("dialog");
      dlg.className = "dialog";
      dlg.innerHTML = '<div class="dialog-body"><h3>' + esc(opts.title) + '</h3><p class="desc">' + esc(opts.body || "") + "</p></div>" +
        '<div class="dialog-footer"><button type="button" class="btn" data-act="no">' + esc(opts.cancel || "Batal") + "</button>" +
        '<button type="button" class="btn ' + (opts.danger ? "btn-danger-solid" : "btn-primary") + '" data-act="yes">' + esc(opts.confirm || "Lanjutkan") + "</button></div>";
      document.body.appendChild(dlg);
      var done = function (v) { dlg.close(); dlg.remove(); resolve(v); };
      dlg.addEventListener("cancel", function (e) { e.preventDefault(); done(false); });
      dlg.addEventListener("click", function (e) {
        if (e.target === dlg) return done(false); // klik di luar kotak
        var act = e.target.closest("[data-act]");
        if (act) done(act.dataset.act === "yes");
      });
      dlg.showModal();
      dlg.querySelector('[data-act="no"]').focus();
    });
  }

  // ---------- form ----------
  function setBusy(btn, busy, busyLabel) {
    if (!btn) return;
    if (busy) {
      btn.dataset.label = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<i data-lucide="loader-circle" class="spin"></i>' + esc(busyLabel || "Memproses…");
      icons(btn);
    } else {
      btn.disabled = false;
      if (btn.dataset.label) btn.innerHTML = btn.dataset.label;
    }
  }
  function fieldError(input, message) {
    var holder = input.closest(".form-row-control") || input.closest(".field") || input.parentElement;
    var old = holder.querySelector(".field-error");
    if (old) old.remove();
    input.removeAttribute("aria-invalid");
    if (!message) return;
    input.setAttribute("aria-invalid", "true");
    var el = document.createElement("div");
    el.className = "field-error";
    el.textContent = message;
    holder.appendChild(el);
  }
  function clearErrors(root) {
    root.querySelectorAll(".field-error").forEach(function (e) { e.remove(); });
    root.querySelectorAll('[aria-invalid="true"]').forEach(function (e) { e.removeAttribute("aria-invalid"); });
    root.querySelectorAll(".form-alert").forEach(function (e) { e.hidden = true; });
  }
  function formAlert(el, message, info) {
    if (!el) return;
    if (!message) { el.hidden = true; return; }
    el.className = "form-alert" + (info ? " form-alert-info" : "");
    el.innerHTML = '<i data-lucide="' + (info ? "info" : "circle-alert") + '"></i><span>' + esc(message) + "</span>";
    el.hidden = false;
    icons(el);
  }

  // ---------- 404 di dalam halaman ----------
  function notFound(target, role) {
    var el = typeof target === "string" ? document.querySelector(target) : target;
    var home = HOME[role] || "/masuk";
    el.innerHTML = '<div class="panel">' + emptyState("Data tidak ditemukan",
      "Mungkin sudah dihapus, atau memang bukan milik akun ini.",
      '<a class="btn btn-primary btn-lg" href="' + home + '"><i data-lucide="arrow-left"></i>Kembali ke beranda</a>') + "</div>";
    icons(el);
  }

  // ---------- sesi ----------
  var meCache = null;
  async function guard(role) {
    var me = await window.api.get("/auth/me");
    if (role && me.role !== role) {
      window.location.replace(HOME[me.role] || "/masuk");
      throw new Error("peran salah");
    }
    meCache = me;
    fillMe(me);
    return me;
  }
  function fillMe(me) {
    document.querySelectorAll('[data-me="username"]').forEach(function (e) { e.textContent = me.username; });
    document.querySelectorAll('[data-me="store_name"]').forEach(function (e) { e.textContent = me.store_name || me.username; });
    document.querySelectorAll('[data-me="initials"]').forEach(function (e) { e.textContent = initials(me.store_name || me.username); });
    document.querySelectorAll('[data-me="role"]').forEach(function (e) { e.textContent = me.role === "store" ? "Admin toko" : "Pembeli"; });
    document.querySelectorAll("[data-me-skeleton]").forEach(function (e) { e.remove(); });
  }

  /** Jalankan halaman: cek login + peran, lalu panggil fn(me). Error 404 → halaman "Data tidak ditemukan". */
  function page(role, fn, notFoundTarget) {
    document.addEventListener("DOMContentLoaded", async function () {
      var me;
      try { me = await guard(role); }
      catch (e) {
        // 401 sudah diarahkan ke /masuk; error lain (server mati, BE belum siap) tetap diberi tahu
        if (e && e.status && e.status !== 401) toast(e.detail || "Tidak bisa memuat sesi.", "error");
        return;
      }
      try { await fn(me); }
      catch (e) {
        if (e && e.status === 404) notFound(notFoundTarget || "#page", me.role);
        else if (e && e.status !== 401) toast(e.detail || "Terjadi kesalahan.", "error");
        if (!(e instanceof window.ApiError)) console.error(e);
      }
      icons();
    });
  }

  // ---------- menu akun ----------
  function bindAccountMenu() {
    document.querySelectorAll("[data-menu]").forEach(function (menu) {
      var trigger = menu.querySelector("[data-menu-trigger]");
      var pop = menu.querySelector(".menu-pop");
      trigger.addEventListener("click", function (e) {
        e.stopPropagation();
        pop.hidden = !pop.hidden;
        trigger.setAttribute("aria-expanded", String(!pop.hidden));
      });
      document.addEventListener("click", function (e) { if (!menu.contains(e.target)) pop.hidden = true; });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape") pop.hidden = true; });
    });
    document.querySelectorAll("[data-logout]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        try { await window.api.post("/auth/logout"); } catch (e) { /* tetap keluar */ }
        window.location.href = "/masuk";
      });
    });
  }

  // ---------- banner mock ----------
  function mockBanner() {
    if (!window.api || !window.api.mock) return;
    var bar = document.createElement("div");
    bar.className = "mock-banner";
    bar.setAttribute("role", "status");
    var isStore = /^\/toko/.test(location.pathname);
    bar.innerHTML = "<span>Mode mock aktif · data contoh, tidak tersambung ke server</span>" +
      '<button type="button" data-mock-role>' + (isStore ? "Lihat sebagai pembeli" : "Lihat sebagai toko") + "</button>" +
      '<button type="button" data-mock-off>Matikan mock</button>';
    document.body.insertBefore(bar, document.body.firstChild);
    bar.querySelector("[data-mock-off]").addEventListener("click", function () {
      window.api.disableMock();
      window.location.href = window.location.pathname + "?mock=0";
    });
    bar.querySelector("[data-mock-role]").addEventListener("click", function () {
      window.location.href = isStore ? "/brankas?role=buyer" : "/toko?role=store";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    mockBanner();
    bindAccountMenu();
    flushToast();
    icons();
  });

  window.App = {
    STATUS: STATUS, ALG_LABEL: ALG_LABEL, HOME: HOME,
    esc: esc, icons: icons,
    fmtBytes: fmtBytes, fmtDate: fmtDate, fmtDateTime: fmtDateTime, fmtNum: fmtNum, initials: initials,
    badge: badge, thumb: thumb, fileKind: fileKind, fileIcon: fileIcon, fileRow: fileRow, emptyState: emptyState,
    toast: toast, toastNext: toastNext, confirm: confirmDialog,
    setBusy: setBusy, fieldError: fieldError, clearErrors: clearErrors, formAlert: formAlert,
    notFound: notFound, guard: guard, page: page,
    get me() { return meCache; }
  };
})();
