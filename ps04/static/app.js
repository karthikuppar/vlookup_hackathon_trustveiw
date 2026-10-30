"use strict";
// PS-04 console. No innerHTML anywhere: all server data goes through textContent.
(function () {
  var root = document.getElementById("app");
  var S = { token: sessionStorage.getItem("ps04_token") || null, me: null, tid: sessionStorage.getItem("ps04_tid") || null, view: null, chat: [], conv: null };

  function el(tag, props) {
    var n = document.createElement(tag);
    props = props || {};
    Object.keys(props).forEach(function (k) {
      var v = props[k];
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined && v !== false) n.setAttribute(k, v === true ? "" : v);
    });
    for (var i = 2; i < arguments.length; i++) add(n, arguments[i]);
    return n;
  }
  function add(n, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) c.forEach(function (x) { add(n, x); });
    else n.appendChild(typeof c === "object" ? c : document.createTextNode(String(c)));
  }
  function badge(text) { return el("span", { class: "badge " + String(text).replace(/[^a-z_]/gi, ""), text: String(text) }); }
  function msgBox() { return el("div", { "aria-live": "polite" }); }
  function say(box, text, ok) { box.replaceChildren(el("div", { class: ok ? "okmsg" : "err", text: text })); }
  function fmt(v) { return v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v); }
  function table(cols, rows) {
    var head = el("tr", null, cols.map(function (c) { return el("th", { text: c[0] }); }));
    var body = rows.map(function (r) {
      return el("tr", null, cols.map(function (c) {
        var v = c[1](r);
        return el("td", null, (v !== null && typeof v === "object") ? v : fmt(v));
      }));
    });
    if (!rows.length) body = [el("tr", null, el("td", { colspan: cols.length, class: "meta", text: "Nothing to show." }))];
    return el("div", { class: "tablewrap" }, el("table", null, el("thead", null, head), el("tbody", null, body)));
  }

  async function api(method, path, body, form) {
    var headers = {};
    if (S.token) headers.Authorization = "Bearer " + S.token;
    var opts = { method: method, headers: headers };
    if (form) opts.body = form;
    else if (body !== undefined) { headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    var r = await fetch(path, opts);
    var data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (r.status === 401 && S.token && path !== "/auth/login") { clearSession(); render(); throw new Error("Session expired. Please sign in again."); }
    if (!r.ok) {
      var d = data && data.detail;
      var e2 = new Error(typeof d === "string" ? d : d ? JSON.stringify(d) : "Request failed (" + r.status + ")");
      e2.data = data; e2.status = r.status;
      throw e2;
    }
    return data;
  }
  function clearSession() {
    S.token = null; S.me = null; S.tid = null; S.view = null; S.chat = []; S.conv = null;
    sessionStorage.removeItem("ps04_token"); sessionStorage.removeItem("ps04_tid");
  }

  // ------------------------------------------------------------ capabilities
  function role() {
    if (!S.me) return null;
    var m = S.me.memberships.filter(function (x) { return x.tenant_id === S.tid; })[0];
    return m ? m.role : null;
  }
  function tenantName(id) {
    var m = S.me.memberships.filter(function (x) { return x.tenant_id === id; })[0];
    return m ? m.name : id;
  }
  function navItems() {
    var items = [];
    if (S.tid) {
      items.push(["chat", "Chat"], ["docs", "Documents"]);
      if (role() === "client_admin") items.push(["members", "Members"], ["sharing", "Sharing"], ["audit", "Audit"]);
    }
    if (S.me.is_sysadmin) items.push(["platform", "Platform admin"]);
    items.push(["security", "Security status"]);
    return items;
  }

  // ------------------------------------------------------------------ shell
  async function boot() {
    if (!S.token) return render();
    try { S.me = await api("GET", "/auth/me"); } catch (e) { clearSession(); }
    if (S.me) {
      var ids = S.me.memberships.map(function (m) { return m.tenant_id; });
      if (ids.indexOf(S.tid) < 0) S.tid = ids[0] || null;
    }
    render();
  }
  function render() {
    root.replaceChildren(S.token && S.me ? shell() : loginView());
    if (S.token && S.me) renderView();
  }
  function loginView() {
    var err = msgBox();
    var email = el("input", { type: "email", placeholder: "Email", autocomplete: "username", required: true });
    var pw = el("input", { type: "password", placeholder: "Password", autocomplete: "current-password", required: true });
    var btn = el("button", { class: "btn", type: "submit", text: "Sign in" });
    var form = el("form", { class: "card login", onsubmit: async function (ev) {
      ev.preventDefault(); btn.disabled = true;
      try {
        var r = await api("POST", "/auth/login", { email: email.value, password: pw.value });
        S.token = r.token; sessionStorage.setItem("ps04_token", S.token);
        await boot();
      } catch (e) { say(err, e.message); btn.disabled = false; }
    } }, el("h2", { text: "PS-04 Knowledge Console" }), el("div", { class: "meta", text: "Sign in to continue" }), el("p"), email, pw, btn, err);
    return form;
  }
  function shell() {
    var nav = el("nav", { class: "side" }, el("div", { class: "brand", text: "PS-04 Console" }));
    var items = navItems();
    if (!S.view || !items.some(function (i) { return i[0] === S.view; })) S.view = items[0][0];
    items.forEach(function (i) {
      nav.appendChild(el("button", { class: S.view === i[0] ? "active" : "", text: i[1], onclick: function () { S.view = i[0]; render(); } }));
    });
    var top = el("div", { class: "top" });
    if (S.me.memberships.length) {
      var sel = el("select", { "aria-label": "Tenant", onchange: function () {
        S.tid = sel.value; sessionStorage.setItem("ps04_tid", S.tid); S.chat = []; S.conv = null; render();
      } }, S.me.memberships.map(function (m) { return el("option", { value: m.tenant_id, text: m.name + " (" + m.role + ")", selected: m.tenant_id === S.tid }); }));
      top.appendChild(el("span", { class: "meta", text: "Tenant" })); top.appendChild(sel);
    } else top.appendChild(el("span", { class: "meta", text: "No tenant memberships" }));
    top.appendChild(el("span", { class: "sp" }));
    top.appendChild(el("span", { text: S.me.name + " <" + S.me.email + ">" + (S.me.is_sysadmin ? " [sysadmin]" : "") }));
    top.appendChild(el("button", { class: "btn sec", text: "Log out", onclick: async function () {
      try { await api("POST", "/auth/logout"); } catch (e) { /* ignore */ }
      clearSession(); render();
    } }));
    return el("div", { class: "shell" }, nav, el("div", { class: "main" }, top, el("div", { class: "view", id: "view" })));
  }
  var VIEWS = { chat: chatView, docs: docsView, members: membersView, sharing: sharingView, audit: auditView, platform: platformView, security: securityView };
  function renderView() {
    var v = document.getElementById("view");
    v.replaceChildren(el("div", { class: "meta", text: "Loading..." }));
    Promise.resolve(VIEWS[S.view](v)).catch(function (e) { v.replaceChildren(el("div", { class: "err", text: e.message })); });
  }
  var T = function (p) { return "/tenants/" + encodeURIComponent(S.tid) + p; };

  // ------------------------------------------------------------------- chat
  function citeLine(c, n) {
    return el("li", null, "[" + n + "] ", el("button", { class: "link", text: c.title, onclick: function () { openCitation(c.chunk_id); } }),
      el("span", { class: "meta", text: " v" + c.version_no + (c.page ? ", p." + c.page : "") + (c.section ? ", § " + c.section : "") + (c.shared_from ? ", shared from " + c.shared_from : "") }),
      c.quote ? el("div", { class: "meta", text: "“" + c.quote + "”" }) : null);
  }
  var chunkBox = null;
  async function openCitation(id) {
    chunkBox.replaceChildren(el("div", { class: "meta", text: "Loading passage..." }));
    try {
      var c = await api("GET", T("/citations/" + encodeURIComponent(id)));
      chunkBox.replaceChildren(el("div", { class: "card" },
        el("h3", { text: c.title + " (v" + c.version_no + ")" }),
        el("div", { class: "meta", text: [c.page ? "page " + c.page : "", c.section ? "section " + c.section : "", "chars " + c.char_start + "-" + c.char_end, c.superseded ? "SUPERSEDED version" : "current", "sha256 " + String(c.sha256).slice(0, 12)].filter(Boolean).join(" | ") }),
        el("div", { class: "chunk", text: c.text }),
        el("button", { class: "btn sec", text: "Close", onclick: function () { chunkBox.replaceChildren(); } })));
    } catch (e) { say(chunkBox, e.message); }
  }
  function answerCard(res) {
    var card = el("div", { class: "msg a" }, badge(res.outcome), el("p", { text: res.answer }));
    if (res.question_flagged) card.appendChild(el("div", { class: "banner", text: "Your question looked like a prompt-injection attempt and was flagged." }));
    if (res.conflicts && res.conflicts.length) {
      res.conflicts.forEach(function (cf) {
        card.appendChild(el("div", null, el("strong", { text: "Conflict: " + cf.kind }),
          el("div", { class: "sbs" }, cf.sources.map(function (s) {
            return el("div", null, el("button", { class: "link", text: s.title + " v" + s.version_no, onclick: function () { openCitation(s.chunk_id); } }),
              el("div", { class: "meta", text: (s.page ? "p." + s.page + " " : "") + (s.shared_from ? "shared from " + s.shared_from : "") }),
              el("p", { text: s.quote || "" }));
          }))));
      });
    }
    if (res.citations && res.citations.length) card.appendChild(el("ol", { class: "cites", style: null }, res.citations.map(citeLine)));
    return card;
  }
  function chatView(v) {
    var log = el("div");
    S.chat.forEach(function (m) { log.appendChild(m.q ? el("div", { class: "msg q", text: m.q }) : answerCard(m.res)); });
    chunkBox = el("div");
    var err = msgBox();
    var ta = el("textarea", { rows: 3, maxlength: 2000, placeholder: "Ask a question about your authorised documents..." });
    var btn = el("button", { class: "btn", text: "Ask", onclick: async function () {
      var q = ta.value.trim(); if (!q) return;
      btn.disabled = true; err.replaceChildren();
      try {
        var res = await api("POST", T("/chat"), { question: q, conversation_id: S.conv });
        S.conv = res.conversation_id; S.chat.push({ q: q }, { res: res }); ta.value = "";
        log.appendChild(el("div", { class: "msg q", text: q })); log.appendChild(answerCard(res));
      } catch (e) { say(err, e.message); }
      btn.disabled = false;
    } });
    v.replaceChildren(el("h2", { text: "Chat" }), log, chunkBox, el("div", { class: "card" }, ta, el("div", { class: "row" }, btn,
      el("button", { class: "btn sec", text: "New conversation", onclick: function () { S.chat = []; S.conv = null; renderView(); } })), err));
  }

  // -------------------------------------------------------------- documents
  async function docsView(v) {
    var docs = await api("GET", T("/documents"));
    var admin = role() === "client_admin";
    var detail = el("div"), out = el("div");
    v.replaceChildren(el("h2", { text: "Documents" }));
    if (admin) {
      var msg = msgBox();
      var file = el("input", { type: "file", required: true });
      var title = el("input", { type: "text", placeholder: "Title (optional)" });
      v.appendChild(el("form", { class: "card", onsubmit: async function (ev) {
        ev.preventDefault();
        var fd = new FormData(); fd.append("file", file.files[0]); if (title.value) fd.append("title", title.value);
        await upload(T("/documents"), fd, msg);
      } }, el("h3", { text: "Upload new document" }), el("div", { class: "row" }, file, title, el("button", { class: "btn", type: "submit", text: "Upload" })), msg));
    }
    out.appendChild(table([
      ["Title", function (d) { return el("button", { class: "link", text: d.title, onclick: function () { showDoc(d.id, detail); } }); }],
      ["Version", function (d) { return d.version_no; }],
      ["Status", function (d) { return badge(d.status || "ready"); }],
      ["Owner", function (d) { return d.shared_from ? "shared from " + d.shared_from : "own"; }],
      ["Uploaded", function (d) { return d.uploaded_at; }],
      ["Error", function (d) { return d.error; }]
    ], docs));
    v.appendChild(el("div", { class: "card" }, out)); v.appendChild(detail);
  }
  async function upload(path, fd, msg) {
    msg.replaceChildren(el("div", { class: "meta", text: "Uploading and ingesting..." }));
    try {
      var r = await api("POST", path, undefined, fd);
      say(msg, "Ingested: status " + r.status + (r.version_no ? ", version " + r.version_no : ""), true);
      setTimeout(renderView, 800);
    } catch (e) {
      var d = e.data && e.data.status ? " [" + e.data.status + (e.data.error ? ": " + e.data.error : "") + "]" : "";
      say(msg, e.message + d);
    }
  }
  async function showDoc(id, box) {
    box.replaceChildren(el("div", { class: "meta", text: "Loading..." }));
    try {
      var d = await api("GET", T("/documents/" + encodeURIComponent(id)));
      var msg = msgBox(), file = el("input", { type: "file", required: true });
      var card = el("div", { class: "card" }, el("h3", { text: d.title + " - version history" }),
        table([["Version", function (x) { return "v" + x.version_no + (x.is_current ? " (current)" : ""); }],
          ["File", function (x) { return x.filename; }], ["Status", function (x) { return x.status ? badge(x.status) : ""; }],
          ["Uploaded", function (x) { return x.uploaded_at; }], ["By", function (x) { return x.uploaded_by; }],
          ["SHA-256", function (x) { return String(x.sha256 || "").slice(0, 16); }],
          ["Superseded", function (x) { return x.superseded_at; }], ["Error", function (x) { return x.error; }]], d.versions));
      if (role() === "client_admin" && !d.versions.some(function (x) { return x.is_current === undefined; }) ) {
        card.appendChild(el("form", { onsubmit: async function (ev) {
          ev.preventDefault(); var fd = new FormData(); fd.append("file", file.files[0]);
          await upload(T("/documents/" + encodeURIComponent(id) + "/versions"), fd, msg);
        } }, el("p"), el("div", { class: "row" }, file, el("button", { class: "btn", type: "submit", text: "Upload new version" })), msg));
      }
      box.replaceChildren(card);
    } catch (e) { say(box, e.message); }
  }

  // ---------------------------------------------------------------- members
  async function membersView(v) {
    var list = await api("GET", T("/members"));
    var msg = msgBox();
    var f = { email: el("input", { type: "email", placeholder: "Email", required: true }), name: el("input", { placeholder: "Name", required: true }),
      pw: el("input", { type: "password", placeholder: "Password (min 10)", minlength: 10, required: true }),
      role: el("select", null, el("option", { value: "employee", text: "employee" }), el("option", { value: "client_admin", text: "client_admin" })) };
    async function act(fn) { try { await fn(); renderView(); } catch (e) { say(msg, e.message); } }
    v.replaceChildren(el("h2", { text: "Members" }),
      el("form", { class: "card", onsubmit: function (ev) { ev.preventDefault();
        act(function () { return api("POST", T("/members"), { email: f.email.value, name: f.name.value, password: f.pw.value, role: f.role.value }); }); } },
        el("h3", { text: "Add member" }), el("div", { class: "row" }, f.email, f.name, f.pw, f.role, el("button", { class: "btn", type: "submit", text: "Add" })), msg),
      el("div", { class: "card" }, table([["Name", function (m) { return m.name; }], ["Email", function (m) { return m.email; }],
        ["Role", function (m) { return m.role; }], ["Status", function (m) { return m.status; }],
        ["", function (m) {
          if (m.status !== "active") return "";
          var other = m.role === "client_admin" ? "employee" : "client_admin";
          return el("span", null,
            el("button", { class: "btn sec", text: "Make " + other, onclick: function () { act(function () { return api("PATCH", T("/members/" + encodeURIComponent(m.id)), { role: other }); }); } }), " ",
            el("button", { class: "btn danger", text: "Remove", onclick: function () { if (confirm("Remove " + m.email + "?")) act(function () { return api("DELETE", T("/members/" + encodeURIComponent(m.id))); }); } }));
        }]], list)));
  }

  // ---------------------------------------------------------------- sharing
  async function sharingView(v) {
    var res = await Promise.all([api("GET", T("/shares")), api("GET", T("/documents"))]);
    var sh = res[0], docs = res[1].filter(function (d) { return !d.shared_from; });
    var msg = msgBox();
    var grantee = el("input", { placeholder: "Grantee tenant id (ten_...)", required: true, size: 28 });
    var docSel = el("select", null, el("option", { value: "", text: "All documents" }), docs.map(function (d) { return el("option", { value: d.id, text: d.title }); }));
    var exp = el("input", { type: "datetime-local", title: "Expires (optional)" });
    function dname(id) { if (!id) return "all documents"; var d = res[1].filter(function (x) { return x.id === id; })[0]; return d ? d.title : id; }
    v.replaceChildren(el("h2", { text: "Sharing" }),
      el("form", { class: "card", onsubmit: async function (ev) { ev.preventDefault();
        var b = { grantee_tenant_id: grantee.value.trim() };
        if (docSel.value) b.document_id = docSel.value;
        if (exp.value) b.expires_at = new Date(exp.value).toISOString().replace(/\.\d+Z$/, "Z");
        try { await api("POST", T("/shares"), b); renderView(); } catch (e) { say(msg, e.message); } } },
        el("h3", { text: "Grant access" }), el("div", { class: "row" }, grantee, docSel, exp, el("button", { class: "btn", type: "submit", text: "Grant" })), msg),
      el("div", { class: "card" }, el("h3", { text: "Outgoing shares" }), table([
        ["Grantee", function (s) { return s.grantee_tenant_id; }], ["Scope", function (s) { return dname(s.document_id); }],
        ["Granted", function (s) { return s.granted_at; }], ["Expires", function (s) { return s.expires_at; }],
        ["State", function (s) { return s.revoked_at ? el("span", null, badge("revoked"), " " + s.revoked_at) : badge("active"); }],
        ["", function (s) { return s.revoked_at ? "" : el("button", { class: "btn danger", text: "Revoke", onclick: async function () {
          try { await api("DELETE", T("/shares/" + encodeURIComponent(s.id))); renderView(); } catch (e) { say(msg, e.message); } } }); }]], sh.outgoing)),
      el("div", { class: "card" }, el("h3", { text: "Incoming shares" }), table([
        ["Owner tenant", function (s) { return s.owner_tenant_id; }], ["Document", function (s) { return s.document_id || "all documents"; }],
        ["Granted", function (s) { return s.granted_at; }], ["Expires", function (s) { return s.expires_at; }]], sh.incoming)));
  }

  // ------------------------------------------------------------------ audit
  function auditTable(rows) {
    return table([["#", function (r) { return r.seq; }], ["Time", function (r) { return r.ts; }], ["Action", function (r) { return r.action; }],
      ["Actor", function (r) { return r.actor; }], ["Tenant", function (r) { return r.tenant_id; }], ["Counterparty", function (r) { return r.counterparty_tenant_id; }],
      ["Details", function (r) { return r.details; }], ["Hash", function (r) { return String(r.hash || "").slice(0, 12); }]], rows);
  }
  function verifyCard() {
    var out = el("div");
    return el("div", { class: "card" }, el("div", { class: "row" }, el("button", { class: "btn", text: "Verify ledger", onclick: async function () {
      out.replaceChildren(el("span", { class: "meta", text: "Verifying..." }));
      try {
        var r = await api("GET", "/audit/verify");
        out.replaceChildren(badge(r.ok ? "ok" : "broken"), " ", el("span", { class: "meta", text: r.ok ? "Hash chain intact." : "Hash chain verification FAILED." }),
          Object.keys(r).length > 1 ? el("pre", { class: "chunk", text: JSON.stringify(r, null, 2) }) : null);
      } catch (e) { say(out, e.message); }
    } })), out);
  }
  async function auditView(v) {
    var rows = await api("GET", T("/audit?limit=200"));
    v.replaceChildren(el("h2", { text: "Audit" }), verifyCard(), el("div", { class: "card" }, auditTable(rows)));
  }

  // --------------------------------------------------------------- platform
  async function platformView(v) {
    var res = await Promise.all([api("GET", "/admin/tenants"), api("GET", "/admin/audit?limit=200")]);
    var tenants = res[0], msg = msgBox();
    async function act(fn, ok) { try { var r = await fn(); say(msg, ok || "Done.", true); setTimeout(renderView, 600); return r; } catch (e) { say(msg, e.message); } }
    var tn = el("input", { placeholder: "New tenant name", minlength: 2, required: true });
    var u = { email: el("input", { type: "email", placeholder: "Email", required: true }), name: el("input", { placeholder: "Name", required: true }),
      pw: el("input", { type: "password", placeholder: "Password (min 10)", minlength: 10, required: true }),
      tid: el("select", null, el("option", { value: "", text: "(no tenant)" }), tenants.map(function (t) { return el("option", { value: t.id, text: t.name }); })),
      role: el("select", null, el("option", { value: "employee", text: "employee" }), el("option", { value: "client_admin", text: "client_admin" })),
      sys: el("input", { type: "checkbox" }) };
    var off = el("input", { placeholder: "User id (usr_...)", size: 24 });
    var cpOut = el("div");
    v.replaceChildren(el("h2", { text: "Platform administration" }), msg,
      el("form", { class: "card", onsubmit: function (ev) { ev.preventDefault(); act(function () { return api("POST", "/admin/tenants", { name: tn.value }); }, "Tenant created."); } },
        el("h3", { text: "Create tenant" }), el("div", { class: "row" }, tn, el("button", { class: "btn", type: "submit", text: "Create" }))),
      el("form", { class: "card", onsubmit: function (ev) { ev.preventDefault();
        var b = { email: u.email.value, name: u.name.value, password: u.pw.value, is_sysadmin: u.sys.checked, role: u.role.value };
        if (u.tid.value) b.tenant_id = u.tid.value;
        act(function () { return api("POST", "/admin/users", b); }, "User created."); } },
        el("h3", { text: "Create user" }), el("div", { class: "row" }, u.email, u.name, u.pw, u.tid, u.role, el("label", null, u.sys, " sysadmin"), el("button", { class: "btn", type: "submit", text: "Create" }))),
      el("div", { class: "card" }, el("h3", { text: "Tenants" }), table([["Name", function (t) { return t.name; }], ["Id", function (t) { return t.id; }],
        ["Status", function (t) { return badge(t.status); }], ["Created", function (t) { return t.created_at; }],
        ["", function (t) { var next = t.status === "active" ? "suspended" : "active";
          return el("button", { class: "btn " + (next === "suspended" ? "danger" : "sec"), text: next === "suspended" ? "Suspend" : "Reactivate",
            onclick: function () { if (confirm(next + " tenant " + t.name + "?")) act(function () { return api("PATCH", "/admin/tenants/" + encodeURIComponent(t.id), { status: next }); }, "Tenant " + next + "."); } }); }]], tenants)),
      el("form", { class: "card", onsubmit: function (ev) { ev.preventDefault();
        if (confirm("Offboard " + off.value + "? This disables the account and revokes all sessions.")) act(function () { return api("POST", "/admin/users/" + encodeURIComponent(off.value.trim()) + "/offboard"); }, "User offboarded."); } },
        el("h3", { text: "Offboard user" }), el("div", { class: "row" }, off, el("button", { class: "btn danger", type: "submit", text: "Offboard" }))),
      el("div", { class: "card" }, el("h3", { text: "Ledger" }), el("div", { class: "row" }, el("button", { class: "btn sec", text: "Write checkpoint", onclick: async function () {
        try { var cp = await api("POST", "/audit/checkpoint"); cpOut.replaceChildren(el("pre", { class: "chunk", text: JSON.stringify(cp, null, 2) })); } catch (e) { say(cpOut, e.message); } } })), cpOut),
      verifyCard(),
      el("div", { class: "card" }, el("h3", { text: "Global audit (metadata)" }), auditTable(res[1])));
  }

  // --------------------------------------------------------------- security
  async function securityView(v) {
    var s = await api("GET", "/security/status");
    var tee = s.tee || {};
    var simulated = !tee.hardware_backed;
    v.replaceChildren(el("h2", { text: "Security status" }),
      el("div", { class: "banner", text: simulated ? "TEE mode: " + tee.mode + ". This is a SIMULATED interface only - no hardware enclave or remote attestation is in use." : "TEE mode: " + tee.mode }),
      el("div", { class: "card" }, table([["Property", function (r) { return r[0]; }], ["Value", function (r) { return r[1]; }]], [
        ["TEE mode", tee.mode], ["Hardware backed", String(!!tee.hardware_backed)], ["Enabled", String(!!tee.enabled)], ["Note", tee.note],
        ["Audit ledger", s.audit_ledger ? s.audit_ledger.type + " - " + s.audit_ledger.anchoring : ""], ["Egress", s.egress], ["Model", s.model]])));
  }

  boot();
})();
