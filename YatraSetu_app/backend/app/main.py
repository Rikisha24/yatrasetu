"""YatraSetu API (FastAPI + SQLite). Serves the built React app from ./static."""
import os
import secrets
from datetime import date, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, engine
from .data import DEFAULTS, SCENARIOS, TRIP

app = FastAPI(title="YatraSetu", version="1.0")
db.init()

STATIC = os.path.join(os.path.dirname(__file__), "..", "static")


class Profile(BaseModel):
    name: str = DEFAULTS["name"]
    budget: int = Field(DEFAULTS["budget"], ge=500)
    hotelBudget: int = Field(DEFAULTS["hotelBudget"], ge=500)
    arriveBy: str = Field(DEFAULTS["arriveBy"], pattern=r"^\d{2}:\d{2}$")
    noNight: bool = DEFAULTS["noNight"]
    mode: str = Field(DEFAULTS["mode"], pattern=r"^(any|flight|train)$")
    group: int = Field(DEFAULTS["group"], ge=1, le=9)
    wCost: int = Field(DEFAULTS["wCost"], ge=0, le=100)
    wTime: int = Field(DEFAULTS["wTime"], ge=0, le=100)
    wComfort: int = Field(DEFAULTS["wComfort"], ge=0, le=100)
    wRisk: int = Field(DEFAULTS["wRisk"], ge=0, le=100)
    consent: bool = DEFAULTS["consent"]


class Overrides(BaseModel):
    budget: Optional[int] = None
    hotelBudget: Optional[int] = None
    noNight: Optional[bool] = None
    group: Optional[int] = None

    def clean(self):
        return {k: v for k, v in self.model_dump().items() if v is not None}


class RecoverReq(BaseModel):
    scenario: str
    overrides: Overrides = Overrides()
    session: str = "anon"


class BookReq(RecoverReq):
    option_id: str
    simulate_drift: bool = False
    simulate_fail: bool = False
    drift_accepted: Optional[bool] = None
    secs: Optional[float] = None


class KeepReq(RecoverReq):
    secs: float = 0


class ChatReq(BaseModel):
    message: str = Field(max_length=500)
    scenario: Optional[str] = None
    overrides: Overrides = Overrides()
    session: str = "anon"


class DraftReq(RecoverReq):
    kind: str = Field(pattern=r"^(refund|hotel|client)$")
    option_id: Optional[str] = None


def profile_now():
    return {**DEFAULTS, **db.get_profile()}


def scn_or_404(key):
    if key not in SCENARIOS:
        raise HTTPException(404, "Unknown scenario")


@app.get("/api/health")
def health():
    return {"ok": True, "llm": engine.llm_configured()}


@app.get("/api/bootstrap")
def bootstrap():
    return {"trip": TRIP, "scenarios": {k: v["label"] for k, v in SCENARIOS.items()},
            "profile": profile_now(), "suggestions": engine.SUGGESTIONS, "llm": engine.llm_configured(),
            "defaults": DEFAULTS}


@app.put("/api/profile")
def put_profile(p: Profile):
    db.save_profile(p.model_dump())
    return p.model_dump()


@app.delete("/api/profile")
def del_profile():
    db.delete_profile()
    return DEFAULTS


@app.post("/api/recover")
def recover(req: RecoverReq):
    scn_or_404(req.scenario)
    out = engine.recover(req.scenario, profile_now(), req.overrides.clean())
    db.log_event(req.session, "search", req.scenario, out["evaluated"], out["removedCount"])
    if out["phase"] == "fallback":
        db.log_event(req.session, "fallback", req.scenario)
    return out


@app.post("/api/book")
def book(req: BookReq):
    scn_or_404(req.scenario)
    try:
        out = engine.book(req.scenario, profile_now(), req.overrides.clean(), req.option_id, req.simulate_drift,
                          req.simulate_fail, req.drift_accepted,
                          lambda: "SBX-" + secrets.token_hex(3).upper())
    except KeyError:
        raise HTTPException(404, "Option no longer available")
    if out["status"] == "confirmed":
        db.log_event(req.session, "recovery", req.scenario, secs=req.secs, delta=out["delta"],
                     top_accepted=out["topAccepted"])
    return out


@app.post("/api/keep")
def keep(req: KeepReq):
    scn_or_404(req.scenario)
    db.log_event(req.session, "recovery", req.scenario, secs=req.secs, delta=0)
    return {"ok": True}


@app.post("/api/chat")
def chat(req: ChatReq):
    if req.scenario:
        scn_or_404(req.scenario)
    reply, ov, rec = engine.chat(req.message, req.scenario, profile_now(), req.overrides.clean())
    if rec is not None:
        db.log_event(req.session, "search", req.scenario, rec["evaluated"], rec["removedCount"])
    return {"reply": reply, "overrides": ov, "recovery": rec}


@app.post("/api/draft")
def draft(req: DraftReq):
    scn_or_404(req.scenario)
    return {"text": engine.draft_text(req.kind, req.scenario, profile_now(), req.overrides.clean(), req.option_id)}


@app.post("/api/support")
def support(req: RecoverReq):
    scn_or_404(req.scenario)
    return {"text": engine.support_summary(req.scenario, profile_now(), req.overrides.clean())}


@app.get("/api/metrics")
def metrics(session: str = "anon"):
    return db.metrics(session)


@app.delete("/api/metrics")
def reset_metrics(session: str = "anon"):
    db.clear_events(session)
    return {"ok": True}


@app.get("/api/ics")
def ics(scenario: str, option_id: str, ref: str = "SBX-000000", budget: Optional[int] = None):
    scn_or_404(scenario)
    ov = {"budget": budget} if budget else {}
    scn = engine.get_scn(scenario)
    c = engine.cons(profile_now(), ov, scn)
    ranked, _ = engine.search_and_rank(scn, c)
    o = next((x for x in ranked if x["id"] == option_id and x.get("dep") is not None), None)
    if not o:
        raise HTTPException(404, "No such option")
    day = (date.today() + timedelta(days=1)).strftime("%Y%m%d")
    return PlainTextResponse(engine.build_ics(o, ref, day), media_type="text/calendar",
                             headers={"Content-Disposition": 'attachment; filename="new-flight.ics"'})


# ---- static front end (built React app); falls back to index.html for the SPA
if os.path.isdir(os.path.join(STATIC, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC, "assets")), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    if path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    f = os.path.normpath(os.path.join(STATIC, path))
    if path and f.startswith(os.path.normpath(STATIC)) and os.path.isfile(f):
        return FileResponse(f)
    index = os.path.join(STATIC, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return PlainTextResponse("Frontend not built yet. Run: cd frontend && npm install && npm run build", 503)
