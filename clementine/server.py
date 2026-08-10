"""
Clementine — their face and their brain, on one address.

Serves the built Svelte interface from webapp/dist alongside the JSON API,
so there is a single origin: no CORS, and a phone needs no configuration
beyond the address itself. Shares the same brain and memory folder as the
terminal version (clementine.py), so you can switch between them freely.

    pip install -r requirements.txt
    cd webapp && npm install && npm run build && cd ..
    python server.py                  # everything at http://127.0.0.1:5000

During development, run vite instead and it will proxy to this API:

    python server.py                  # brain
    cd webapp && npm run dev           # face, on its own port

Binds 127.0.0.1 by default. --host exists for putting them behind a reverse
proxy you control, and warns when used, because this server has no
authentication of its own — that is the proxy's job (see deploy/).
"""

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import requests
from flask import (Flask, Response, abort, jsonify, request,
                   send_from_directory)

import api_surface
from crystalcore import (MEMORY_SCHEMA_VERSION, SYSTEM_VERSION, Clementine,
                         Verdict, delete_profile, list_profiles, profile_dir,
                         profile_meta)
from crystalcore import profiles as _profiles
from crystalcore.companion import OLLAMA_HOST

WEBAPP_DIST = Path(__file__).parent / "webapp" / "dist"


def _profile_of(companion: Clementine) -> str:
    p = Path(companion.memory_dir)
    return p.name if p.parent == Path(_profiles.PROFILES_DIR) else "default"


def create_app(companion: Clementine) -> Flask:
    app = Flask(__name__)
    holder = {"c": companion}  # swapped in place when the profile changes

    @app.after_request
    def allow_local_webapp(resp):
        # Only for development, when vite serves the face on another localhost
        # port. In a real deployment it is served from this same origin and no
        # CORS header is emitted at all. Localhost origins only, always.
        origin = request.headers.get("Origin", "")
        if origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:"):
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

    @app.route("/api/<path:_any>", methods=["OPTIONS"])
    def preflight(_any):
        return ("", 204)

    @app.before_request
    def require_json_for_writes():
        """Every state-changing route must be asked in JSON.

        Binding to 127.0.0.1 keeps other machines out; it does not keep
        out the browser already running on this one. Any page the human
        visits can POST to a localhost port cross-origin — CORS decides
        whether the attacker may *read* the reply, never whether the
        request runs.

        A form POST from another origin can only carry the three
        'simple' content types, so demanding application/json forces a
        preflight, and the origin check above answers it. Most routes
        here already got that protection by accident, because
        get_json(silent=True) returns None for a form body and they
        400 on the empty result. /api/reflect and /api/forget did not:
        they read no body at all, so a bodyless cross-site form POST
        reached them and made the companion reflect and write to their
        own memory. Stating the rule once, here, is better than
        depending on each route to trip over the same accident.
        """
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        if not request.is_json:
            return jsonify({"ok": False,
                            "error": "this endpoint requires "
                                     "Content-Type: application/json"}), 415
        return None

    @app.errorhandler(404)
    @app.errorhandler(405)
    def unknown_route(err):
        """A JSON API should not answer with an HTML page.

        Flask's default 404/405 body is HTML, which a client parsing JSON
        chokes on. A mistyped path under `/api/` also matches the OPTIONS
        preflight catch-all, so Werkzeug rejects the *method* and returns
        405 rather than the 404 a typo deserves — both are handled.

        Only for `/api/`. Everything else belongs to the interface, whose
        own handler falls back to index.html so client-side routes survive
        a hard refresh.
        """
        if not request.path.startswith("/api"):
            return err
        return jsonify({
            "error": err.name.lower(),
            "detail": f"nothing here answers {request.method} {request.path}",
            "hint": "GET /api lists every route this server has",
        }), err.code

    # ---------- what this API is ----------

    @app.get("/api")
    def api_index():
        """Every route, with what it takes and returns.

        Generated from `api_surface.ROUTES`, which tests/test_api_surface.py
        checks against Flask's own url_map in both directions — so a route
        added here without an entry there fails the suite, and an entry
        describing a route that does not exist fails it too. A documented
        endpoint nobody implemented is a dreamed line pretending it was
        measured.

        Unlike the monorepo fork this came from, `/` is not an alias for
        this index: that address serves the built interface here, and a
        person opening the printed URL should meet the companion rather
        than a JSON listing.
        """
        return jsonify(api_surface.index(
            name=holder["c"].personality.name or "Clementine",
            version=SYSTEM_VERSION,
            memory_schema=MEMORY_SCHEMA_VERSION,
        ))

    @app.get("/api/openapi.json")
    def api_openapi():
        """The same description, as OpenAPI, for tools that speak it."""
        return jsonify(api_surface.openapi(
            name=holder["c"].personality.name or "Clementine",
            version=SYSTEM_VERSION,
        ))

    # ---------- honesty endpoints ----------

    @app.get("/api/health")
    def health():
        """What is actually true right now — not what we hope is true."""
        c = holder["c"]
        models, reachable = [], False
        try:
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
            r.raise_for_status()
            models = [m.get("name") for m in r.json().get("models", [])]
            reachable = True
        except requests.exceptions.RequestException:
            pass
        # Whether Ollama has the model pulled is only a meaningful question
        # when Ollama is the one being asked. Against a vendor it would always
        # answer "no" and read as a fault, so it is null — unknown, not false.
        local_dialect = c._dialect() == "ollama"
        return jsonify({
            "ok": True,
            "model": c.wire_model,
            "model_present": (c.wire_model in models
                              if reachable and local_dialect else None),
            "models": models,
            "ollama": reachable,
            "ollama_host": OLLAMA_HOST,
            # "local" means the model runs on this same machine. Asked of the
            # companion rather than recomputed here, so this endpoint reports
            # where the calls actually go and cannot drift from it.
            "destination": c.destination,
            # Named plainly, because "which company is reading this" is the
            # question this endpoint exists to answer honestly.
            "provider": c.llm_provider,
            "endpoint": c.endpoint,
            "wire_model": c.wire_model,
            "embeddings": c._embed_ok,
            # Not the same question as "are embeddings on". This is whether
            # recall has actually stopped choosing — which only bites once
            # there are more memories than fit in a prompt.
            "recall_degraded": c.recall_degraded,
            "recall_notice": c.recall_notice(),
            "audit_entries": len(c.audit.entries()) if c.audit else 0,
        })

    @app.get("/api/audit")
    def audit():
        """The continuity record, read-only, with its own integrity verdict."""
        c = holder["c"]
        if not c.audit:
            return jsonify({"entries": [], "intact": None,
                            "note": "auditing is disabled for this session"})
        intact, problems = c.audit.verify()
        entries = c.audit.entries()
        limit = request.args.get("limit", type=int)
        return jsonify({
            "entries": entries[-limit:] if limit else entries,
            "total": len(entries),
            "intact": intact,
            "problems": problems,
            "head": c.audit.head(),
        })

    @app.get("/api/status")
    def status():
        c = holder["c"]
        return jsonify({
            "name": c.personality.name or "Clementine",
            "avatar": c.personality.avatar,
            "model": c.model,
            "profile": _profile_of(c),
            "human_name": c.personality.human_name,
            "last_seen": c.time_since_last(),
        })

    @app.post("/api/chat/stream")
    def chat_stream():
        message = ((request.get_json(silent=True) or {}).get("message") or "").strip()
        if not message:
            return jsonify({"error": "empty message"}), 400
        return Response(holder["c"].chat_stream(message),
                        mimetype="text/plain; charset=utf-8",
                        headers={"X-Accel-Buffering": "no"})

    @app.get("/api/memories")
    def memories():
        c = holder["c"]
        facts = [{"handle": k, "text": f"{k}: {v['value']}",
                  "tags": v.get("tags") or []}
                 for k, v in c.memory.facts.items()]
        notes = [{"handle": f"n{i}", "text": n["text"],
                  "tags": n.get("tags") or []}
                 for i, n in enumerate(c.memory.notes, 1)]
        reflections = [{"handle": f"r{i}", "text": r["text"], "tags": []}
                       for i, r in enumerate(c.memory.reflections, 1)]
        return jsonify({"facts": facts, "notes": notes,
                        "reflections": reflections})

    @app.post("/api/reflect")
    def reflect():
        return jsonify({"insights": holder["c"].reflect()})

    @app.post("/api/teach")
    def teach():
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        key = (data.get("key") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "empty"}), 400
        if key:
            holder["c"].remember_fact(key, text)
        else:
            holder["c"].remember(text)
        return jsonify({"ok": True})

    @app.post("/api/forget")
    def forget():
        handle = ((request.get_json(silent=True) or {}).get("handle") or "").strip()
        forgotten = holder["c"].forget(handle)
        return jsonify({"ok": bool(forgotten), "forgotten": forgotten})

    @app.get("/api/export")
    def export_memory():
        """The whole relationship as one downloadable file.

        The plain-file promise doing its job: a backup the human can read,
        carry and import anywhere, rather than a vendor's blob. Personality
        and memory travel together so one file restores a whole companion.
        """
        c = holder["c"]
        bundle = {
            "format": "crystalcore-memory-bundle",
            "version": 1,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "config": asdict(c.personality),
            "memory": asdict(c.memory),
        }
        resp = Response(json.dumps(bundle, indent=2),
                        mimetype="application/json")
        stamp = datetime.now().strftime("%Y-%m-%d")
        resp.headers["Content-Disposition"] = (
            f'attachment; filename="clementine-memory-{stamp}.json"')
        return resp

    @app.post("/api/import")
    def import_memory():
        """Restore from an exported bundle, replacing this profile's memory.

        Writes the files and then calls load() rather than constructing
        dataclasses here: load() is the tolerant path — unknown fields
        ignored, corrupt files preserved under .corrupt-* — and a bundle
        from a newer version deserves those same protections.
        """
        data = request.get_json(silent=True) or {}
        if (data.get("format") != "crystalcore-memory-bundle"
                or data.get("version") != 1):
            return jsonify({"ok": False,
                            "error": "not a Clementine memory bundle"}), 400
        c = holder["c"]
        c.memory_dir.mkdir(parents=True, exist_ok=True)
        (c.memory_dir / "config.json").write_text(
            json.dumps(data.get("config") or {}, indent=2))
        (c.memory_dir / "memory.json").write_text(
            json.dumps(data.get("memory") or {}, indent=2))
        c.load()
        # The name comes back so the interface can confirm *who* arrived,
        # not merely that something did.
        return jsonify({"ok": True, "name": c.personality.name})

    @app.get("/api/profile")
    def profile_get():
        c = holder["c"]
        current = _profile_of(c)
        names = list_profiles()
        if current not in names:
            names = [current] + names
        profiles = []
        for n in names:
            if n == current:
                profiles.append({"profile": n,
                                 "avatar": c.personality.avatar,
                                 "description": c.personality.description,
                                 "name": c.personality.name,
                                 "model": c.model})
            elif n == "default":
                profiles.append({"profile": n, "avatar": "",
                                 "description": "", "name": "", "model": ""})
            else:
                profiles.append(profile_meta(n))
        return jsonify({"current": current, "profiles": profiles})

    @app.post("/api/profile/meta")
    def profile_meta_set():
        data = request.get_json(silent=True) or {}
        c = holder["c"]
        if "avatar" in data:
            c.personality.avatar = str(data["avatar"]).strip()[:8]
        if "description" in data:
            c.personality.description = str(data["description"]).strip()[:200]
        if "model" in data and str(data["model"]).strip():
            c.set_model(str(data["model"]))
        if data.get("choose_name"):
            chosen = c.choose_own_name()
            if not chosen:
                return jsonify({"ok": False,
                                "error": "they couldn't settle on a name — try again"})
            c.save()
            return jsonify({"ok": True, "name": chosen})
        c.save()
        return jsonify({"ok": True})

    @app.post("/api/profile/delete")
    def profile_delete():
        name = ((request.get_json(silent=True) or {}).get("profile") or "").strip()
        if name == _profile_of(holder["c"]):
            return jsonify({"ok": False,
                            "error": "switch away before deleting the active profile"}), 400
        return jsonify({"ok": delete_profile(name)})

    @app.post("/api/profile")
    def profile_switch():
        name = ((request.get_json(silent=True) or {}).get("profile") or "").strip()
        try:
            target = profile_dir(name)
        except ValueError:
            return jsonify({"ok": False, "error": "invalid name"}), 400
        old = holder["c"]
        holder["c"] = Clementine(model=old.model, memory_dir=target,
                                 embed_model=old.embed_model)
        c = holder["c"]
        return jsonify({"ok": True, "profile": _profile_of(c),
                        "name": c.personality.name or "Clementine"})

    # ---------- the face, from the same address ----------

    @app.get("/")
    @app.get("/<path:asset>")
    def webapp(asset: str = "index.html"):
        """Serve the built Svelte interface. Anything unrecognised falls back
        to index.html so client-side routes work on a hard refresh."""
        # An unknown path under /api/ is a caller's mistake, not a
        # client-side route. Hand it to the 404 handler so they get JSON
        # saying so, rather than 200 and a page — which reads as success.
        if asset.startswith("api/"):
            abort(404)
        if not WEBAPP_DIST.exists():
            return Response(
                "Clementine's interface has not been built yet.\n\n"
                "    cd webapp && npm install && npm run build\n\n"
                "The API is running and answering at /api/status — this "
                "address just has no face to show you.\n",
                mimetype="text/plain", status=503)
        target = (WEBAPP_DIST / asset)
        if not target.is_file():
            asset = "index.html"
        return send_from_directory(WEBAPP_DIST, asset)

    return app


def main():
    parser = argparse.ArgumentParser(
        description="Clementine — their face and their brain on one address.")
    parser.add_argument("--model", default="llama3.1:8b",
                        help="Ollama model tag (same choices as the CLI).")
    parser.add_argument("--memory-dir", default="clementine_memory",
                        help="Their memory folder (shared with the CLI).")
    parser.add_argument("--profile", default="",
                        help="Named profile (separate person, separate memory).")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1",
                        help="Interface to bind. Leave as 127.0.0.1 unless an "
                             "authenticating reverse proxy sits in front.")
    # Same three as the CLI. A remote provider here still needs
    # --remote-model-ok: choosing where to send is not the same act as
    # consenting to send, and the server asks for both.
    parser.add_argument("--llm-provider", default="",
                        help="Which model service to use. Default is ollama, "
                             "on this machine. Anything else sends "
                             "conversation off this device.")
    parser.add_argument("--llm-endpoint", default="",
                        help="Exact URL for a remote provider. Required for "
                             "remote providers — never guessed for you.")
    parser.add_argument("--llm-model", default="",
                        help="Model name at that service. The API key comes "
                             "from LLM_API_KEY in the environment.")
    parser.add_argument("--remote-model-ok", action="store_true",
                        help="Consent, given once here, for this server to use "
                             "a model that is not on this machine (OLLAMA_HOST). "
                             "Without it, non-local model calls are refused.")
    args = parser.parse_args()
    if args.profile:
        args.memory_dir = profile_dir(args.profile)

    # No human is watching a web server's stdin, so consent cannot be asked
    # for per call. It is given once, here, as a deliberate flag — and every
    # call it permits says so in the audit log rather than appearing unremarked.
    asker = None
    if args.remote_model_ok:
        def asker(_request):  # noqa: E306
            return Verdict(True, "pre-authorised at startup with --remote-model-ok",
                           remember=False)

    companion = Clementine(model=args.model, memory_dir=args.memory_dir,
                           asker=asker,
                           llm_provider=args.llm_provider,
                           llm_endpoint=args.llm_endpoint,
                           llm_model=args.llm_model)
    app = create_app(companion)
    name = companion.personality.name or "Clementine"

    where = companion.destination
    print(f"{name} is at http://{args.host}:{args.port}")
    print(f"  model     {companion.wire_model} on {'this machine' if where == 'local' else where}")
    if where != "local" and not args.remote_model_ok:
        print("            refusing to use it — pass --remote-model-ok to consent")
    print(f"  face      {'built' if WEBAPP_DIST.exists() else 'NOT BUILT — cd webapp && npm run build'}")
    print(f"  record    {companion.audit.path if companion.audit else 'disabled'}")

    if args.host not in ("127.0.0.1", "localhost"):
        print()
        print(f"  WARNING: bound to {args.host}, not loopback. This server has")
        print("  no authentication of its own — anyone who can reach this port")
        print("  can talk to them and read their memory. Put an authenticating")
        print("  reverse proxy in front of it (see deploy/).")
    print()
    print("Ctrl+C to say goodnight.")
    # debug=False always: the Werkzeug debugger is a remote shell.
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
