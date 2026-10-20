/* Profil & KTP: GET /profile?alg=, PUT /profile, POST /files (id_card) */
(function () {
  "use strict";
  var FIELDS = [
    "full_name",
    "nik",
    "birth_date",
    "gender",
    "nationality",
    "marital_status",
    "address",
    "phone",
    "bank_account",
    "religion",
    "health_notes",
  ];
  var loaded = null,
    alg = "aes",
    busy = false;
  function $(id) {
    return document.getElementById(id);
  }

  function fill(profile) {
    var form = $("profile-form");
    FIELDS.forEach(function (k) {
      form[k].value = profile.data[k] == null ? "" : profile.data[k];
    });
    $("updated-at").textContent = profile.updated_at
      ? "Disimpan " + App.fmtDateTime(profile.updated_at)
      : "Belum pernah disimpan";
    $("decrypt-ms").textContent = App.fmtNum(profile.decrypt_ms, 2) + " ms";
    $("decrypt-alg").textContent = "GET /profile?alg=" + profile.algorithm;
  }

  function renderKtp(profile) {
    var frame = $("ktp-frame");
    if (!profile.id_card_file_id) {
      frame.innerHTML =
        '<div class="empty-state" style="padding:16px"><i data-lucide="id-card"></i><span class="desc">Belum ada foto KTP</span></div>';
      $("ktp-change").lastChild.textContent = "Unggah foto";
      $("ktp-meta").textContent = "";
    } else {
      var f = { id: profile.id_card_file_id, category: "id_card", name: "ktp" };
      frame.innerHTML =
        '<img alt="Foto KTP" src="' + App.esc(api.fileUrl(f, alg)) + '">';
      $("ktp-meta").textContent =
        "Terenkripsi · dibuka dengan " + App.ALG_LABEL[alg];
    }
    App.icons(frame);
  }

  async function load() {
    var p = await api.get("/profile?alg=" + alg);
    loaded = p;
    fill(p);
    renderKtp(p);
  }

  function validate(form) {
    var bad = false,
      d = loaded ? loaded.data : {};
    var v = function (k) {
      return form[k].value.trim();
    };
    if (!v("full_name")) {
      App.fieldError(form.full_name, "Nama lengkap wajib diisi.");
      bad = true;
    }
    // Nilai lama (mis. yang tersamar dari server) tidak divalidasi ulang
    if (v("nik") && v("nik") !== d.nik && !/^\d{16}$/.test(v("nik"))) {
      App.fieldError(form.nik, "NIK harus 16 digit angka.");
      bad = true;
    }
    if (
      v("phone") &&
      v("phone") !== d.phone &&
      !/^\+?[0-9]{9,15}$/.test(v("phone").replace(/[\s-]/g, ""))
    ) {
      App.fieldError(form.phone, "Nomor HP belum valid.");
      bad = true;
    }
    return !bad;
  }

  async function save(e) {
    e.preventDefault();
    var form = $("profile-form");
    App.clearErrors(form);
    if (!validate(form)) {
      form.querySelector('[aria-invalid="true"]').focus();
      return;
    }
    var data = {};
    FIELDS.forEach(function (k) {
      data[k] = form[k].value.trim() || null;
    });
    var btn = $("submit");
    App.setBusy(btn, true, "Mengenkripsi…");
    try {
      var p = await api.put("/profile", { data: data });
      loaded = Object.assign({}, loaded, p);
      fill(loaded);
      $("welcome").hidden = true;
      App.toast("Profil tersimpan dan terenkripsi");
    } catch (err) {
      App.formAlert($("form-alert"), err.detail);
    }
    App.setBusy(btn, false);
  }

  async function changeKtp(file) {
    if (!file || busy) return;
    var btn = $("ktp-change");
    var bad = !/\.(jpe?g|png)$/i.test(file.name)
      ? "Foto KTP harus JPG atau PNG."
      : file.size > 5 * 1024 * 1024
        ? "Foto " + App.fmtBytes(file.size) + " melebihi batas 5 MB."
        : null;
    App.fieldError(btn, bad);
    if (bad) return;
    busy = true;
    var bar = $("ktp-progress");
    bar.hidden = false;
    bar.className = "progress";
    App.setBusy(btn, true, "Mengunggah…");
    var fd = new FormData();
    fd.append("category", "id_card");
    fd.append("file", file);
    try {
      var f = await api.upload("/files", fd, function (p) {
        bar.firstElementChild.style.width = Math.round(p * 100) + "%";
      });
      bar.className = "progress is-done";
      loaded.id_card_file_id = f.id;
      App.setBusy(btn, false);
      renderKtp(loaded);
      App.toast("Foto KTP tersimpan dan terenkripsi");
    } catch (err) {
      bar.className = "progress is-error";
      App.setBusy(btn, false);
      App.fieldError(btn, err.detail);
    }
    busy = false;
    setTimeout(function () {
      bar.hidden = true;
      bar.firstElementChild.style.width = "0";
    }, 1200);
  }

  App.page("buyer", async function () {
    if (new URLSearchParams(location.search).get("baru") === "1")
      $("welcome").hidden = false;
    document.querySelectorAll("[data-sensitive]").forEach(function (i) {
      i.classList.add("masked");
    });
    document.querySelectorAll("[data-reveal]").forEach(function (b) {
      b.addEventListener("click", function () {
        var input = $(b.dataset.reveal);
        var hidden = input.classList.toggle("masked");
        b.innerHTML =
          '<i data-lucide="' +
          (hidden ? "eye" : "eye-off") +
          '"></i>' +
          (hidden ? "Tampilkan" : "Sembunyikan");
        App.icons(b);
      });
    });
    document.querySelectorAll(".sidebar-link").forEach(function (a) {
      a.addEventListener("click", function () {
        document.querySelectorAll(".sidebar-link").forEach(function (x) {
          x.classList.toggle("is-active", x === a);
        });
      });
    });
    $("profile-form").addEventListener("submit", save);
    $("reset").addEventListener("click", function () {
      App.clearErrors($("profile-form"));
      if (loaded) fill(loaded);
      App.toast("Perubahan dibatalkan", "info");
    });
    $("ktp-change").addEventListener("click", function () {
      $("ktp-input").click();
    });
    $("ktp-input").addEventListener("change", function () {
      changeKtp(this.files[0]);
      this.value = "";
    });
    $("alg").addEventListener("change", async function () {
      alg = this.value;
      $("decrypt-ms").innerHTML =
        '<span class="skeleton skeleton-text" style="width:80px"></span>';
      try {
        await load();
        App.toast(
          "Profil didekripsi ulang dengan " + App.ALG_LABEL[alg],
          "info",
        );
      } catch (err) {
        App.toast(err.detail, "error");
      }
    });
    await load();
  });
})();
