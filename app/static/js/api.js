/* Awan — satu modul untuk semua panggilan API.
 *
 * api.get(path) · api.post(path, body) · api.put(path, body) · api.patch(path, body) · api.del(path)
 * api.upload(path, formData, onProgress)  — XMLHttpRequest supaya ada progress upload
 * api.fileUrl(file, alg)                   — URL media/unduhan (/files/{id}/download?alg=)
 *
 * Error dilempar sebagai ApiError {status, detail}. Status 401 → redirect ke /masuk?next=...
 * (kecuali api.get(path, {noRedirect: true}), dipakai halaman publik untuk sekadar mengecek sesi).
 *
 * Mode mock: aktif kalau URL berisi ?mock=1 atau localStorage.awanMock === '1'.
 * ?mock=1 menyimpan pilihan itu di localStorage supaya tetap aktif saat pindah halaman; ?mock=0 mematikannya.
 * ?role=store / ?role=buyer memilih akun mock. Perubahan disimpan di sessionStorage (tab ini saja).
 */
(function () {
  "use strict";

  // ---------- penyimpanan aman (bisa diblokir browser) ----------
  function lsGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { if (v == null) window.localStorage.removeItem(k); else window.localStorage.setItem(k, v); } catch (e) { /* abaikan */ } }
  function ssGet(k) { try { return window.sessionStorage.getItem(k); } catch (e) { return null; } }
  function ssSet(k, v) { try { if (v == null) window.sessionStorage.removeItem(k); else window.sessionStorage.setItem(k, v); } catch (e) { /* abaikan */ } }

  var params = new URLSearchParams(window.location.search);
  if (params.get("mock") === "1") lsSet("awanMock", "1");
  if (params.get("mock") === "0") { lsSet("awanMock", null); ssSet("awanMockState", null); }
  var MOCK = params.get("mock") !== "0" && (params.get("mock") === "1" || lsGet("awanMock") === "1");

  function ApiError(status, detail) {
    this.name = "ApiError";
    this.status = status;
    this.detail = detail || "Terjadi kesalahan. Coba lagi sebentar lagi.";
    this.message = this.detail;
  }
  ApiError.prototype = Object.create(Error.prototype);

  function detailFrom(body, status) {
    if (body && typeof body.detail === "string") return body.detail;
    if (body && Array.isArray(body.detail)) {
      // Validasi FastAPI (422): ambil pesan pertama yang bisa dibaca
      return body.detail.map(function (d) { return d.msg || String(d); }).join(", ");
    }
    if (status === 413) return "File terlalu besar.";
    if (status === 404) return "Data tidak ditemukan.";
    if (status >= 500) return "Server sedang bermasalah. Coba lagi sebentar lagi.";
    return null;
  }

  function redirectToLogin(path) {
    var here = window.location.pathname + window.location.search;
    if (window.location.pathname === "/masuk" || window.location.pathname === "/daftar") return;
    var q = "?next=" + encodeURIComponent(here);
    // /auth/me dipanggil di setiap halaman; kalau belum masuk sama sekali tidak perlu pesan "sesi berakhir"
    if (path !== "/auth/me") q += "&sesi=habis";
    window.location.replace("/masuk" + q);
  }

  function isAuthForm(path) { return path.indexOf("/auth/login") === 0 || path.indexOf("/auth/register") === 0; }

  function finish(status, body, path, opts) {
    if (status >= 200 && status < 300) return body;
    if (status === 401 && !isAuthForm(path) && !(opts && opts.noRedirect)) {
      redirectToLogin(path);
      throw new ApiError(401, "Sesi berakhir, silakan masuk lagi");
    }
    throw new ApiError(status, detailFrom(body, status));
  }

  // ---------- mode nyata ----------
  async function realRequest(method, path, body, ropts) {
    var opts = { method: method, credentials: "same-origin", headers: { Accept: "application/json" } };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    var res;
    try { res = await fetch(path, opts); }
    catch (e) { throw new ApiError(0, "Tidak bisa terhubung ke server. Cek koneksi lalu coba lagi."); }
    var text = await res.text();
    var data = null;
    if (text) { try { data = JSON.parse(text); } catch (e) { data = null; } }
    return finish(res.status, data, path, ropts);
  }

  function realUpload(path, formData, onProgress) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", path);
      xhr.withCredentials = true;
      xhr.setRequestHeader("Accept", "application/json");
      xhr.upload.onprogress = function (e) {
        if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
      };
      xhr.onload = function () {
        var data = null;
        try { data = xhr.responseText ? JSON.parse(xhr.responseText) : null; } catch (e) { data = null; }
        try { resolve(finish(xhr.status, data, path)); } catch (err) { reject(err); }
      };
      xhr.onerror = function () { reject(new ApiError(0, "Upload terputus. Cek koneksi lalu coba lagi.")); };
      xhr.send(formData);
    });
  }

  // ---------- mode mock ----------
  var DELAY = 300;
  var STATE_KEY = "awanMockState";
  var state = null;
  var blobUrls = {}; // id file → object URL untuk file yang baru diupload di halaman ini
  var wait = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var clone = function (o) { return o == null ? o : JSON.parse(JSON.stringify(o)); };
  var nowIso = function () {
    var d = new Date(), off = -d.getTimezoneOffset(), sign = off >= 0 ? "+" : "-";
    var pad = function (n) { return String(Math.floor(Math.abs(n))).padStart(2, "0"); };
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + "T" + pad(d.getHours()) + ":" +
      pad(d.getMinutes()) + ":" + pad(d.getSeconds()) + sign + pad(off / 60) + ":" + pad(off % 60);
  };

  async function loadJson(name) {
    var res = await fetch("/static/mock/" + name + ".json", { cache: "no-store" });
    return res.json();
  }

  function save() { ssSet(STATE_KEY, JSON.stringify(state)); }

  async function db() {
    if (state) return state;
    var raw = ssGet(STATE_KEY);
    if (raw) { try { state = JSON.parse(raw); } catch (e) { state = null; } }
    if (!state) {
      var names = ["auth-me", "auth-me-store", "profile", "packages", "package-3", "files", "stats", "stores", "claims", "claim-5"];
      var all = await Promise.all(names.map(loadJson));
      var j = {}; names.forEach(function (n, i) { j[n] = all[i]; });
      var claimDetails = { 5: j["claim-5"] };
      // Klaim lain di claims.json dibuat detailnya dari ringkasan
      j.claims.items.forEach(function (c) {
        if (claimDetails[c.id]) return;
        claimDetails[c.id] = {
          id: c.id, status: c.status,
          message: c.id === 7 ? "Bantalan telinga kiri sobek saat kotak dibuka." : "Unit tidak bisa diisi daya sejak dibuka.",
          created_at: c.created_at,
          package: { id: c.package_id, item_name: c.item_name, order_no: c.order_no },
          buyer: { name: c.buyer_name, ktp_verified: c.id !== 7 },
          store: { id: 21, store_name: c.store_name },
          files: [{ id: c.video_file_id, category: "video", name: "unboxing-" + c.package_id + ".mp4", mime_type: "video/mp4", size_bytes: 31457280 }],
          replies: c.status === "diterima"
            ? [{ id: 90 + c.id, author_role: "store", author_name: c.store_name, body: "Klaim diterima, unit pengganti kami kirim besok.", created_at: c.created_at }]
            : []
        };
      });
      state = {
        session: "in",
        role: "buyer",
        me: { buyer: j["auth-me"], store: j["auth-me-store"] },
        profile: j.profile,
        packages: j.packages.items.map(function (p) {
          return { id: p.id, item_name: p.item_name, store: p.store, order_no: p.order_no, created_at: p.created_at };
        }),
        packageClaims: { 3: j["package-3"].claim },
        files: j.files.items,
        stats: j.stats,
        stores: j.stores,
        claims: j.claims.items,
        claimDetails: claimDetails,
        nextId: 100
      };
    }
    var role = params.get("role");
    if (role === "store" || role === "buyer") { state.role = role; state.session = "in"; }
    save();
    return state;
  }

  function newId() { state.nextId += 1; return state.nextId; }
  function me() { return clone(state.me[state.role]); }
  function filesOf(pkgId) { return state.files.filter(function (f) { return f.package_id === pkgId; }); }

  function packageSummary(p) {
    var fs = filesOf(p.id);
    var video = fs.filter(function (f) { return f.category === "video"; })[0];
    return {
      id: p.id, item_name: p.item_name, store: p.store, order_no: p.order_no, created_at: p.created_at,
      video_file_id: video ? video.id : null,
      document_count: fs.filter(function (f) { return f.category === "document"; }).length,
      total_size_bytes: fs.reduce(function (s, f) { return s + f.size_bytes; }, 0)
    };
  }
  function packageDetail(p) {
    return {
      id: p.id, item_name: p.item_name, store: p.store, order_no: p.order_no, created_at: p.created_at,
      files: clone(filesOf(p.id)),
      claim: clone(state.packageClaims[p.id] || null)
    };
  }

  function err(status, detail) { return { status: status, body: { detail: detail } }; }
  function ok(body, status) { return { status: status || 200, body: clone(body) }; }

  var routes = [
    ["GET", /^\/auth\/me$/, function () {
      return state.session === "in" ? ok(me()) : err(401, "Belum masuk");
    }],
    ["POST", /^\/auth\/login$/, function (m, body) {
      if (!body || !body.username || !body.password) return err(400, "Isi username dan password dulu.");
      if (body.password === "salah") return err(401, "Username atau password salah.");
      state.role = /elektra|toko/i.test(body.username) ? "store" : "buyer";
      if (state.role === "buyer") state.me.buyer.username = body.username;
      state.session = "in";
      return ok(me());
    }],
    ["POST", /^\/auth\/register$/, function (m, body) {
      if (!body || !body.username || !body.password) return err(400, "Isi username dan password dulu.");
      if (body.username.toLowerCase() === "dzaky") return err(400, "Username sudah dipakai. Coba yang lain.");
      if (body.password.length < 8) return err(400, "Password minimal 8 karakter.");
      state.role = "buyer";
      state.me.buyer.username = body.username;
      state.session = "in";
      return ok(me(), 201);
    }],
    ["POST", /^\/auth\/logout$/, function () { state.session = "out"; return ok({ ok: true }); }],

    ["GET", /^\/profile$/, function (m, body, q) {
      var alg = q.get("alg") || "aes";
      if (["aes", "rc4", "des"].indexOf(alg) < 0) return err(400, "Algoritma tidak dikenal.");
      var base = { aes: 0.42, rc4: 0.31, des: 1.87 }[alg];
      var p = clone(state.profile);
      p.algorithm = alg;
      p.decrypt_ms = Math.round((base + Math.random() * 0.08) * 100) / 100;
      return ok(p);
    }],
    ["PUT", /^\/profile$/, function (m, body) {
      if (!body || !body.data) return err(400, "Data profil kosong.");
      if (body.data.nik && !/^[0-9x]{16}$/i.test(body.data.nik)) return err(400, "NIK harus 16 digit.");
      state.profile.data = Object.assign({}, state.profile.data, body.data);
      state.profile.updated_at = nowIso();
      return ok(Object.assign({}, state.profile, { algorithm: "aes", decrypt_ms: 0.42 }));
    }],

    ["GET", /^\/packages$/, function () {
      var items = state.packages.slice().sort(function (a, b) { return b.created_at.localeCompare(a.created_at); });
      return ok({ items: items.map(packageSummary) });
    }],
    ["POST", /^\/packages$/, function (m, body) {
      if (!body || !body.item_name || !body.item_name.trim()) return err(400, "Nama barang wajib diisi.");
      var p = { id: newId(), item_name: body.item_name.trim(), store: (body.store || "").trim(), order_no: (body.order_no || "").trim(), created_at: nowIso() };
      state.packages.push(p);
      return ok(packageDetail(p), 201);
    }],
    ["GET", /^\/packages\/(\d+)$/, function (m) {
      var p = state.packages.filter(function (x) { return x.id === +m[1]; })[0];
      return p ? ok(packageDetail(p)) : err(404, "Paket tidak ditemukan.");
    }],

    ["GET", /^\/files$/, function (m, body, q) {
      var cat = q.get("category");
      return ok({ items: state.files.filter(function (f) { return !cat || f.category === cat; }) });
    }],
    ["DELETE", /^\/files\/(\d+)$/, function (m) {
      var before = state.files.length;
      state.files = state.files.filter(function (f) { return f.id !== +m[1]; });
      return before === state.files.length ? err(404, "File tidak ditemukan.") : ok(null, 204);
    }],

    ["GET", /^\/stats$/, function () { return ok(state.stats); }],
    ["GET", /^\/stores$/, function () { return ok(state.stores); }],

    ["GET", /^\/claims$/, function () {
      var mine = state.role === "store"
        ? state.claims.filter(function (c) { return c.store_name === state.me.store.store_name; })
        : state.claims.filter(function (c) { return state.packages.some(function (p) { return p.id === c.package_id; }); });
      return ok({ items: mine.slice().sort(function (a, b) { return b.created_at.localeCompare(a.created_at); }) });
    }],
    ["POST", /^\/claims$/, function (m, body) {
      if (!body || !body.package_id || !body.store_user_id) return err(400, "Pilih toko tujuan dulu.");
      if (!body.message || !body.message.trim()) return err(400, "Tulis keluhanmu dulu.");
      var p = state.packages.filter(function (x) { return x.id === +body.package_id; })[0];
      if (!p) return err(404, "Paket tidak ditemukan.");
      if (state.packageClaims[p.id]) return err(400, "Paket ini sudah punya klaim.");
      var store = state.stores.items.filter(function (s) { return s.id === +body.store_user_id; })[0];
      if (!store) return err(400, "Toko tidak ditemukan.");
      var id = newId(), created = nowIso(), fs = filesOf(p.id);
      var video = fs.filter(function (f) { return f.category === "video"; })[0];
      var buyerName = state.profile.data.full_name || state.me.buyer.username;
      state.claims.push({ id: id, package_id: p.id, item_name: p.item_name, order_no: p.order_no, buyer_name: buyerName,
        store_name: store.store_name, status: "diajukan", video_file_id: video ? video.id : null, created_at: created });
      state.claimDetails[id] = {
        id: id, status: "diajukan", message: body.message.trim(), created_at: created,
        package: { id: p.id, item_name: p.item_name, order_no: p.order_no },
        buyer: { name: buyerName, ktp_verified: !!state.profile.id_card_file_id },
        store: { id: store.id, store_name: store.store_name },
        files: fs.filter(function (f) { return f.category !== "id_card"; }).map(function (f) {
          return { id: f.id, category: f.category, name: f.name, mime_type: f.mime_type, size_bytes: f.size_bytes };
        }),
        replies: []
      };
      state.packageClaims[p.id] = { id: id, status: "diajukan" };
      return ok({ id: id, status: "diajukan" }, 201);
    }],
    ["GET", /^\/claims\/(\d+)$/, function (m) {
      var c = state.claimDetails[+m[1]];
      return c ? ok(c) : err(404, "Klaim tidak ditemukan.");
    }],
    ["PATCH", /^\/claims\/(\d+)$/, function (m, body) {
      var c = state.claimDetails[+m[1]];
      if (!c) return err(404, "Klaim tidak ditemukan.");
      if (state.role !== "store") return err(403, "Hanya toko yang bisa mengubah status klaim.");
      if (["diajukan", "ditinjau", "diterima", "ditolak"].indexOf(body && body.status) < 0) return err(400, "Pilih keputusan dulu.");
      c.status = body.status;
      if (body.reply && body.reply.trim()) {
        c.replies.push({ id: newId(), author_role: "store", author_name: state.me.store.store_name, body: body.reply.trim(), created_at: nowIso() });
      }
      state.claims.forEach(function (x) { if (x.id === c.id) x.status = c.status; });
      if (state.packageClaims[c.package.id]) state.packageClaims[c.package.id].status = c.status;
      return ok(c);
    }],
    ["POST", /^\/claims\/(\d+)\/replies$/, function (m, body) {
      var c = state.claimDetails[+m[1]];
      if (!c) return err(404, "Klaim tidak ditemukan.");
      if (!body || !body.body || !body.body.trim()) return err(400, "Balasan masih kosong.");
      var isStore = state.role === "store";
      var reply = { id: newId(), author_role: isStore ? "store" : "buyer",
        author_name: isStore ? state.me.store.store_name : c.buyer.name, body: body.body.trim(), created_at: nowIso() };
      c.replies.push(reply);
      return ok(reply, 201);
    }]
  ];

  async function mockRequest(method, path, body, ropts) {
    await db();
    await wait(DELAY);
    var url = new URL(path, window.location.origin);
    for (var i = 0; i < routes.length; i++) {
      var r = routes[i];
      var m = r[0] === method && url.pathname.match(r[1]);
      if (m) {
        var out = r[2](m, clone(body), url.searchParams);
        save();
        return finish(out.status, out.body, url.pathname, ropts);
      }
    }
    return finish(404, { detail: "Endpoint mock belum ada: " + method + " " + url.pathname }, url.pathname);
  }

  async function mockUpload(path, formData, onProgress) {
    await db();
    var file = formData.get("file");
    var category = formData.get("category");
    var pkgId = formData.get("package_id");
    var size = file ? file.size : 0;
    // Simulasi progress: makin besar file makin lama, maks. ±2,6 detik
    var total = 600 + Math.min(2000, size / (50 * 1024 * 1024) * 1000);
    var steps = Math.max(6, Math.round(total / 80));
    for (var i = 1; i <= steps; i++) {
      await wait(total / steps);
      if (onProgress) onProgress(i / steps);
    }
    if (!file) return finish(400, { detail: "File belum dipilih." }, path);
    if (["id_card", "document", "video"].indexOf(category) < 0) return finish(400, { detail: "Kategori file tidak dikenal." }, path);
    var limits = { video: 100, document: 20, id_card: 5 };
    if (size > limits[category] * 1024 * 1024) return finish(413, { detail: "File melebihi " + limits[category] + " MB." }, path);
    var f = {
      id: newId(), package_id: pkgId ? +pkgId : null, category: category, name: file.name,
      mime_type: file.type || "application/octet-stream", size_bytes: size, created_at: nowIso(), algorithms: ["aes", "rc4", "des"]
    };
    state.files.push(f);
    if (category === "id_card") {
      var old = state.profile.id_card_file_id;
      state.files = state.files.filter(function (x) { return !(x.category === "id_card" && x.id === old); });
      state.profile.id_card_file_id = f.id;
    }
    try { blobUrls[f.id] = URL.createObjectURL(file); } catch (e) { /* abaikan */ }
    save();
    return clone(f);
  }

  function mockFileUrl(file) {
    if (blobUrls[file.id]) return blobUrls[file.id];
    var category = file.category, name = (file.name || "").toLowerCase();
    if (category === "video") return "/static/mock/sample.mp4";
    if (category === "id_card") return "/static/mock/ktp-contoh.png";
    if (/\.docx?$/.test(name)) return "/static/mock/docs/kronologi.docx";
    return "/static/mock/docs/invoice-elektra.pdf";
  }

  // ---------- antarmuka publik ----------
  function request(method, path, body, opts) {
    return MOCK ? mockRequest(method, path, body, opts) : realRequest(method, path, body, opts);
  }

  window.ApiError = ApiError;
  window.api = {
    mock: MOCK,
    get: function (path, opts) { return request("GET", path, undefined, opts); },
    post: function (path, body) { return request("POST", path, body === undefined ? {} : body); },
    put: function (path, body) { return request("PUT", path, body); },
    patch: function (path, body) { return request("PATCH", path, body); },
    del: function (path) { return request("DELETE", path); },
    upload: function (path, formData, onProgress) {
      return MOCK ? mockUpload(path, formData, onProgress) : realUpload(path, formData, onProgress);
    },
    /** URL media/unduhan. `file` minimal {id}; di mode mock butuh juga {category, name}. */
    fileUrl: function (file, alg) {
      if (typeof file === "number") file = { id: file };
      if (MOCK) return mockFileUrl(file);
      return "/files/" + file.id + "/download?alg=" + (alg || "aes");
    },
    disableMock: function () { lsSet("awanMock", null); ssSet("awanMockState", null); },
    resetMock: function () { ssSet("awanMockState", null); }
  };
})();
