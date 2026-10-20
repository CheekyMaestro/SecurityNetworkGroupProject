/* Masuk & Daftar */
(function () {
  "use strict";

  function safeNext() {
    var next = new URLSearchParams(location.search).get("next");
    return next && next.charAt(0) === "/" && next.charAt(1) !== "/" ? next : null;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var alertEl = document.getElementById("form-alert");

    document.querySelectorAll("[data-toggle-pw]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var input = document.getElementById(btn.dataset.togglePw);
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        btn.innerHTML = '<i data-lucide="' + (show ? "eye-off" : "eye") + '"></i>' + (show ? "Sembunyikan" : "Lihat");
        App.icons(btn);
      });
    });

    // ---------- Masuk ----------
    var login = document.getElementById("login-form");
    if (login) {
      if (new URLSearchParams(location.search).get("sesi") === "habis") {
        App.formAlert(alertEl, "Sesi berakhir, silakan masuk lagi.", true);
      }
      login.username.focus();
      login.addEventListener("submit", async function (e) {
        e.preventDefault();
        App.clearErrors(login);
        var username = login.username.value.trim(), password = login.password.value;
        var bad = false;
        if (!username) { App.fieldError(login.username, "Isi username dulu."); bad = true; }
        if (!password) { App.fieldError(login.password, "Isi password dulu."); bad = true; }
        if (bad) return;
        var btn = document.getElementById("submit");
        App.setBusy(btn, true, "Memeriksa…");
        try {
          var me = await api.post("/auth/login", { username: username, password: password });
          location.href = safeNext() || App.HOME[me.role] || "/brankas";
        } catch (err) {
          // Pesan umum: tidak menyebut field mana yang salah
          App.formAlert(alertEl, err.status === 401 || err.status === 400 ? "Username atau password salah." : err.detail);
          App.setBusy(btn, false);
          login.password.select();
        }
      });
    }

    // ---------- Daftar ----------
    var reg = document.getElementById("register-form");
    if (reg) {
      reg.username.focus();
      reg.addEventListener("submit", async function (e) {
        e.preventDefault();
        App.clearErrors(reg);
        var username = reg.username.value.trim(), password = reg.password.value, password2 = reg.password2.value;
        var bad = false;
        if (!/^[a-z0-9._]{3,32}$/.test(username)) { App.fieldError(reg.username, "Gunakan 3–32 huruf kecil, angka, titik, atau garis bawah."); bad = true; }
        if (password.length < 8) { App.fieldError(reg.password, "Password minimal 8 karakter."); bad = true; }
        if (password2 !== password) { App.fieldError(reg.password2, "Konfirmasi belum sama dengan password."); bad = true; }
        if (bad) return;
        var btn = document.getElementById("submit");
        App.setBusy(btn, true, "Membuat akun…");
        try {
          await api.post("/auth/register", { username: username, password: password });
          // Masuk otomatis (aman juga kalau register sudah memasang cookie)
          await api.post("/auth/login", { username: username, password: password });
          App.toastNext("Akun dibuat. Lengkapi profilmu dulu, ya.");
          location.href = "/profil?baru=1";
        } catch (err) {
          App.formAlert(alertEl, err.detail);
          App.setBusy(btn, false);
        }
      });
    }
  });
})();
