"""YatraSetu decision engine.

Design rule: code decides every number (filtering, ranking, refund rules, net cost).
The language model, when configured, only *explains*, and a validator rejects any
text whose rupee amounts or times do not match the data.
"""
import json
import math
import os
import re
import urllib.request

from .data import DEFAULTS, HOTELS, NOW, RULES, SCENARIOS, TRANSPORT, TRIP

# ---------------------------------------------------------------- helpers


def jsround(x):
    """JavaScript Math.round (halves round up), so numbers match the prototype."""
    return int(math.floor(x + 0.5))


def num(x):
    return int(x) if float(x) == int(x) else x


def inr(n):
    n = jsround(n)
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + "₹" + s


def hm(m):
    d = m // 1440
    m = m % 1440
    return f"{m // 60:02d}:{m % 60:02d}" + (" +1d" if d > 0 else "")


def parse_hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def dur(m):
    return f"{m // 60}h {m % 60}m"


def cons(profile, ov, scn):
    c = {**DEFAULTS, **profile, **(ov or {})}
    if scn and scn.get("group") and (ov or {}).get("group") is None:
        c["group"] = scn["group"]
    c["arrMin"] = parse_hm(c["arriveBy"])
    return c


def get_scn(key):
    scn = SCENARIOS.get(key)
    if scn is None:
        raise KeyError(key)
    return {**scn, "key": key}


# ---------------------------------------------------------------- impact analysis


def analyze(scn, c):
    f, h, m = TRIP["bookings"][0], TRIP["bookings"][1], TRIP["bookings"][2]
    items, keep = [], False
    if scn["type"] == "flight":
        cancelled = scn["status"] == "cancelled"
        new_arr = math.inf if cancelled else f["arr"] + scn["delay"]
        rule = RULES[f["airline"]]
        if cancelled:
            items.append({"id": "F1", "st": "bad", "text": "Cancelled. " + rule["cancel"] + "."})
        else:
            eligible = scn["delay"] / 60 >= rule["delayHours"]
            items.append({"id": "F1", "st": "bad" if new_arr > c["arrMin"] else "warn",
                          "text": f"Now departs {hm(f['dep'] + scn['delay'])}, lands {hm(new_arr)}. "
                                  + (rule["delayRule"] + " — eligible." if eligible
                                     else f"Below the {rule['delayHours']} h refund threshold.")})
        late_ci = (not cancelled) and new_arr + 45 > h["checkin"]
        if cancelled:
            ci = ("warn", "Check-in 14:00 at risk until a new arrival is set.")
        elif late_ci:
            ci = ("warn", f"Arrival ~{hm(new_arr + 45)} is after 14:00 check-in. Late check-in notice needed.")
        else:
            ci = ("ok", "Check-in 14:00 unaffected.")
        items.append({"id": "H1", "st": ci[0], "text": ci[1]})
        if cancelled:
            items.append({"id": "M1", "st": "bad", "text": "17:00 meeting is missed unless an alternative is found."})
        else:
            buffer = m["at"] - (new_arr + 60)
            items.append({"id": "M1", "st": "bad" if buffer < 0 else "warn" if buffer < 60 else "ok",
                          "text": "17:00 meeting will be missed." if buffer < 0
                          else f"Still reachable with {dur(buffer)} to spare."})
        items.append({"id": "F2", "st": "ok", "text": "Return flight on Day 2 is unaffected."})
        keep = (not cancelled) and new_arr <= c["arrMin"]
    else:
        items.append({"id": "F1", "st": "ok", "text": "Flight unaffected."})
        items.append({"id": "H1", "st": "bad", "text": "Room cancelled by hotel. Night 1 has no stay."})
        items.append({"id": "M1", "st": "warn",
                      "text": "Meeting is unaffected but travel from a new hotel must stay short."})
        items.append({"id": "F2", "st": "ok", "text": "Return flight on Day 2 is unaffected."})
    return {"items": items, "keep": keep}


# ---------------------------------------------------------------- search, filter, rank (plain code)


def is_night(o):
    a, b = o["dep"] % 1440, o["arr"] % 1440

    def n(x):
        return x >= 1320 or x < 300

    return n(a) or n(b)


def search_transport(c, scn):
    kept, removed = [], []
    for o in TRANSPORT:
        why = None
        if scn.get("flightsDown") and o["mode"] in ("flight", "multi"):
            why = "Airport closed, service unavailable"
        elif o["seats"] < c["group"]:
            why = f"Only {o['seats']} seat{'s' if o['seats'] > 1 else ''} left, need {c['group']}"
        elif o["price"] > c["budget"]:
            why = f"Over budget ({inr(o['price'])} vs {inr(c['budget'])})"
        elif o["dep"] < NOW + 60:
            why = "Departs too soon to reach the airport"
        elif c["noNight"] and is_night(o):
            why = "Night travel (hard rule)"
        elif o["arr"] > c["arrMin"]:
            why = f"Arrives {hm(o['arr'])}, after your {c['arriveBy']} deadline"
        if why:
            removed.append({**o, "why": why})
        else:
            kept.append(dict(o))
    return kept, removed


def rank_transport(lst, c):
    if not lst:
        return []
    w = {"cost": c["wCost"], "time": c["wTime"], "comfort": c["wComfort"], "risk": c["wRisk"]}
    tot = sum(w.values()) or 1
    prices = [o["price"] for o in lst]
    lo, hi = min(prices), max(prices)

    def rel(v):
        return 1 if hi == lo else (hi - v) / (hi - lo)

    out = []
    for o in lst:
        cost = rel(o["price"])
        time = max(0, min(1, (c["arrMin"] - o["arr"]) / max(1, c["arrMin"] - (NOW + 190))))
        comfort = o["comfort"] / 5
        g = c["group"]
        risk = 1 if o["seats"] >= g + 4 else .65 if o["seats"] >= g + 2 else .4 if o["seats"] > g else .2
        score = (w["cost"] * cost + w["time"] * time + w["comfort"] * comfort + w["risk"] * risk) / tot
        if c["mode"] != "any" and o["mode"] != c["mode"] and not (c["mode"] == "flight" and o["mode"] == "multi"):
            score *= .92
        out.append({**o, "score": jsround(score * 100),
                    "sub": {"cost": cost, "time": time, "comfort": comfort, "risk": risk}})
    return sorted(out, key=lambda x: -x["score"])


def search_hotels(c):
    kept, removed = [], []
    for o in HOTELS:
        why = None
        if o["price"] > c["hotelBudget"]:
            why = f"Over hotel budget ({inr(o['price'])} vs {inr(c['hotelBudget'])})"
        elif o["dist"] > 8:
            why = f"{o['dist']} km from the meeting, too far"
        if why:
            removed.append({**o, "why": why})
        else:
            kept.append({**o, "kind": "hotel"})
    return kept, removed


def rank_hotels(lst, c):
    out = []
    for o in lst:
        d = 1 - o["dist"] / 8
        p = max(0, 1 - o["price"] / c["hotelBudget"])
        r = max(0, (o["rating"] - 3) / 2)
        out.append({**o, "score": jsround((0.4 * d + 0.2 * p + 0.4 * r) * 100),
                    "sub": {"cost": p, "time": d, "comfort": r, "risk": 1 if o["freeCancel"] else .4}})
    return sorted(out, key=lambda x: -x["score"])


def search_and_rank(scn, c):
    if scn["type"] == "hotel":
        kept, removed = search_hotels(c)
        return rank_hotels(kept, c), removed
    kept, removed = search_transport(c, scn)
    return rank_transport(kept, c), removed


# ---------------------------------------------------------------- explanation layer


def refund_amount(scn):
    f = TRIP["bookings"][0]
    eligible = scn.get("status") == "cancelled" or scn.get("delay", 0) / 60 >= RULES["IndiGo"]["delayHours"]
    return f["price"] if eligible else 0


def net_delta(o, scn):
    if o.get("kind") == "hotel":
        return o["price"] - TRIP["bookings"][1]["price"]
    return o["price"] - refund_amount(scn)


def template_explain(o, i, ranked, c, scn):
    best = ranked[0]
    if o.get("kind") == "hotel":
        t = (f"{o['name']} is {num(o['dist'])} km from your meeting at {inr(o['price'])} a night, rated {num(o['rating'])}. "
             + ("Free cancellation." if o["freeCancel"] else "Not refundable."))
        if i > 0:
            dd = round(o["dist"] - best["dist"], 1)
            t += (f" Compared with {best['name']}, it is {num(abs(dd))} km {'farther' if dd > 0 else 'closer'} "
                  f"and {inr(abs(o['price'] - best['price']))} {'more' if o['price'] > best['price'] else 'cheaper'}.")
        return t
    buf = 1020 - (o["arr"] + 60)
    t = (f"{o['name']} leaves at {hm(o['dep'])} and reaches Mumbai at {hm(o['arr'])}, "
         f"leaving about {dur(buf)} before your 17:00 meeting. ")
    d = net_delta(o, scn)
    if d > 0:
        t += f"It costs {inr(o['price'])}, {inr(d)} more than your original fare after the refund."
    elif d < 0:
        t += f"It costs {inr(o['price'])}, {inr(-d)} less than your original fare."
    else:
        t += f"It costs {inr(o['price'])}, the same as your original fare."
    if i > 0:
        dp, da = o["price"] - best["price"], o["arr"] - best["arr"]
        price_part = inr(-dp) + " cheaper" if dp < 0 else inr(dp) + " dearer" if dp > 0 else "same price"
        time_part = dur(da) + " later" if da > 0 else dur(-da) + " earlier" if da < 0 else "at the same time"
        t += f" Versus the top pick: {price_part}, lands {time_part}."
    if o["seats"] <= c["group"] + 1:
        t += f" Only {o['seats']} seat{'s' if o['seats'] > 1 else ''} left, so book first."
    return t


def validate_text(text, ranked, c, scn):
    """Every rupee amount and HH:MM in the text must be derivable from the data."""
    ok = set()

    def add(v):
        ok.add(str(v).replace(" +1d", ""))

    add("17:00")
    add(c["arriveBy"])
    for r in ranked:
        add(inr(r["price"]))
        if r.get("dep") is not None:
            add(hm(r["dep"]))
            add(hm(r["arr"]))
        if r.get("dist") is not None:
            add(r["dist"])
            add(r["rating"])
    add(inr(c["budget"]))
    for r in ranked:
        for b in ranked:
            if r.get("dist") is not None:
                add(f"{abs(r['dist'] - b['dist']):.1f}")
            add(inr(abs(r["price"] - b["price"])))
            if r.get("arr") is not None:
                add(dur(abs(r["arr"] - b["arr"])))
        add(inr(abs(net_delta(r, scn))))
        if r.get("arr") is not None:
            add(dur(1020 - (r["arr"] + 60)))
        add(r.get("seats"))
    money = re.findall(r"₹\d(?:[\d,]*\d)?", text)
    times = re.findall(r"\b\d{2}:\d{2}\b", text)
    return all(x in ok for x in money + times)


def masked_payload(ranked, c, scn):
    return {
        "traveller": "Traveller 1",
        "group_size": c["group"],
        "constraints": {"max_budget_inr": c["budget"], "arrive_by": c["arriveBy"], "no_night": c["noNight"]},
        "disruption": {"type": scn["type"], "status": scn.get("status") or "room_cancelled",
                       "delay_min": scn.get("delay")},
        "options": [{"id": o["id"], "mode": o.get("mode") or "hotel", "price_inr": o["price"],
                     "dep": hm(o["dep"]) if o.get("dep") is not None else None,
                     "arr": hm(o["arr"]) if o.get("arr") is not None else None,
                     "seats_left": o.get("seats"), "score": o["score"]} for o in ranked],
    }


def llm_configured():
    return bool(os.environ.get("LLM_API_URL") and os.environ.get("LLM_API_KEY"))


def llm_explain(payload):
    """Optional: any OpenAI-compatible chat-completions endpoint. Receives MASKED data only."""
    body = {
        "model": os.environ.get("LLM_MODEL", "default"),
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": (
                "You help a stranded traveller choose between travel options. For each of the first three options "
                "write at most two plain sentences. Use ONLY the numbers given. Reply with JSON only, "
                "shaped like {\"<option id>\": \"<text>\"}.")},
            {"role": "user", "content": json.dumps(payload)},
        ],
    }
    req = urllib.request.Request(
        os.environ["LLM_API_URL"], data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["LLM_API_KEY"]})
    with urllib.request.urlopen(req, timeout=8) as r:
        raw = json.loads(r.read())["choices"][0]["message"]["content"]
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    return json.loads(raw)


def build_explanations(ranked, c, scn):
    expl = {}
    top = ranked[:3]
    for i, o in enumerate(top):
        expl[o["id"]] = {"text": template_explain(o, i, ranked, c, scn), "verified": True, "src": "template"}
    if llm_configured() and c.get("consent", True):
        try:
            texts = llm_explain(masked_payload(ranked, c, scn))
            for o in top:
                t = texts.get(o["id"])
                if isinstance(t, str) and t and validate_text(t, ranked, c, scn):
                    expl[o["id"]] = {"text": t, "verified": True, "src": "llm"}
        except Exception:
            pass  # fall back to the template text
    for o in top:
        e = expl[o["id"]]
        e["verified"] = validate_text(e["text"], ranked, c, scn)
    return expl


# ---------------------------------------------------------------- one decision pass


def decide(scn, c, animate=True, lead=None):
    """Search, filter, rank and explain. Returns everything the UI needs plus the agent log lines."""
    log = list(lead or [])
    if animate:
        log.append({"msg": "Searching nearby hotels…" if scn["type"] == "hotel"
                    else "Searching flights, trains, buses and multi-leg routes…"})
    ranked, removed = search_and_rank(scn, c)
    total = len(ranked) + len(removed)
    log.append({"msg": f"Evaluated {total} options. Removed {len(removed)} that break your rules."})
    if removed:
        reasons = {}
        for o in removed:
            k = o["why"].split(" (")[0].split(",")[0]
            reasons[k] = reasons.get(k, 0) + 1
        log.append({"msg": "Why: " + "; ".join(f"{k} ×{v}" for k, v in reasons.items())})
    for o in ranked:
        o["net"] = net_delta(o, scn)
    res = analyze(scn, c)
    out = {"evaluated": total, "removedCount": len(removed), "ranked": ranked, "removed": removed,
           "expl": {}, "impact": res["items"], "payload": None}
    if not ranked:
        log.append({"msg": "No option passes the hard rules. Handing over to a human, with a summary.", "k": "b"})
        out.update(phase="fallback", log=log)
        return out
    log.append({"msg": f"Ranked {len(ranked)} option{'s' if len(ranked) > 1 else ''} in code "
                       "(cost, time, comfort, availability)."})
    expl = build_explanations(ranked, c, scn)
    log.append({"msg": "Explanations written. Every number checked against the data ✓", "k": "g"})
    keep = res["keep"] and scn["type"] == "flight"
    if keep:
        log.append({"msg": "Delayed flight still meets your deadline. Recommending: keep booking, "
                           "notify hotel and client.", "k": "g"})
    else:
        log.append({"msg": f"Top pick: {ranked[0]['name']}. Waiting for your approval. Nothing is booked yet.",
                    "k": "g"})
    out.update(expl=expl, phase="keep" if keep else "options", log=log,
               payload=masked_payload(ranked, c, scn))
    return out


def constraint_view(c, scn, ov):
    return {"budget": c["hotelBudget"] if scn["type"] == "hotel" else c["budget"], "arriveBy": c["arriveBy"],
            "noNight": c["noNight"], "group": c["group"], "mode": c["mode"], "isHotel": scn["type"] == "hotel",
            "override": bool(ov), "weights": {"cost": c["wCost"], "time": c["wTime"], "comfort": c["wComfort"],
                                              "risk": c["wRisk"]}}


def recover(scn_key, profile, ov):
    scn = get_scn(scn_key)
    c = cons(profile, ov, scn)
    res = analyze(scn, c)
    hit = [i for i in res["items"] if i["st"] != "ok"]
    types = ", ".join(next(b["type"] for b in TRIP["bookings"] if b["id"] == i["id"]) for i in hit)
    budget_txt = inr(c["hotelBudget"] if scn["type"] == "hotel" else c["budget"])
    cond = ("within 8 km of meeting" if scn["type"] == "hotel" else "arrive by " + c["arriveBy"])
    extra = (", no night travel" if scn["type"] == "flight" and c["noNight"] else "") + \
            (f", {c['group']} travellers" if c["group"] > 1 else "")
    lead = [
        {"msg": "Polling status feeds for 4 bookings…", "reveal": "detect"},
        {"msg": "⚠ Detected: " + scn["title"], "k": "w", "mark": "t0"},
        {"msg": f"Impact: {len(hit)} of 4 bookings affected ({types})", "k": "w", "reveal": "impact"},
        {"msg": f"Constraints loaded from profile: budget {budget_txt}, {cond}{extra}"},
    ]
    out = decide(scn, c, animate=True, lead=lead)
    out.update(scenario={**scn}, constraints=constraint_view(c, scn, ov), impact=res["items"])
    return out


def research(scn_key, profile, ov, lead_msg):
    """Re-run the search for this trip after the traveller changes a rule in chat."""
    scn = get_scn(scn_key)
    c = cons(profile, ov, scn)
    out = decide(scn, c, animate=False, lead=[{"msg": lead_msg}])
    out.update(scenario={**scn}, constraints=constraint_view(c, scn, ov))
    return out


# ---------------------------------------------------------------- booking: re-check → hold → update → confirm / roll back


def step_names(o):
    if o.get("kind") == "hotel":
        return ["Re-check price & rooms", "Hold the room", "Update travel to meeting", "Confirm booking"]
    return ["Re-check price & seats", "Hold the seat", "Update hotel & client", "Confirm booking"]


def book(scn_key, profile, ov, option_id, simulate_drift, simulate_fail, drift_accepted, ref_factory):
    scn = get_scn(scn_key)
    c = cons(profile, ov, scn)
    ranked, _ = search_and_rank(scn, c)
    o = next((x for x in ranked if x["id"] == option_id), None)
    if o is None:
        raise KeyError(option_id)
    names = step_names(o)
    st = ["wait"] * 4
    tl = []

    def ev(msg=None, k="", steps=None):
        tl.append({"msg": msg, "k": k, "steps": list(steps if steps is not None else st)})

    resumed = drift_accepted is not None
    if not resumed:
        st[0] = "run"
        ev("Approved by traveller: " + o["name"], "g")
        if simulate_drift:
            np_ = o["price"] + 300
            ev(f"Re-check: price moved {inr(o['price'])} → {inr(np_)}. Asking traveller.", "w")
            return {"status": "needs_price_approval", "from": o["price"], "to": np_, "steps": names,
                    "timeline": tl, "option": o}
    else:
        st[0] = "run"
        if not drift_accepted:
            tl.append({"msg": "Traveller declined the new price. Nothing booked.", "k": "w", "steps": ["wait"] * 4})
            return {"status": "declined", "steps": names, "timeline": tl, "option": o}
        o = {**o, "price": o["price"] + 300}
        ev()
    st[0] = "ok"
    ev("Re-check passed: price and availability confirmed.")
    st[1] = "run"
    ev()
    st[1] = "ok"
    ev(("Room" if o.get("kind") == "hotel" else "Seat") + " held for 10 minutes (sandbox).")
    st[2] = "run"
    ev()
    if simulate_fail:
        st[2] = "fail"
        ev("Step 3 failed (hotel system timeout). Rolling back…", "b")
        ev("Hold released. Original plan untouched. No partial booking.", "g")
        return {"status": "rolled_back", "steps": names, "timeline": tl, "option": o}
    st[2] = "ok"
    ev("Hotel and client notices drafted.")
    st[3] = "run"
    ev()
    ref = ref_factory()
    st[3] = "ok"
    ev("Confirmed " + ref + ". Now tracking the new journey for further disruptions.", "g")
    return {"status": "confirmed", "steps": names, "timeline": tl, "option": o, "ref": ref,
            "delta": net_delta(o, scn), "topAccepted": ranked[0]["id"] == o["id"]}


# ---------------------------------------------------------------- drafts and support summary


def draft_text(kind, scn_key, profile, ov, option_id=None):
    scn = get_scn(scn_key)
    c = cons(profile, ov, scn)
    ranked, _ = search_and_rank(scn, c)
    o = next((x for x in ranked if x["id"] == option_id), None) or (ranked[0] if ranked else None)
    f = TRIP["bookings"][0]
    name = profile.get("name") or DEFAULTS["name"]
    cancelled = scn.get("status") == "cancelled"
    if kind == "refund":
        what = "was cancelled by the airline" if cancelled else f"was delayed by {num(scn['delay'] / 60)} hours"
        policy = RULES["IndiGo"]["cancel"] if cancelled else RULES["IndiGo"]["delayRule"]
        return (f"Subject: Refund request, booking {TRIP['pnr']}\n\nHello IndiGo support,\n\n"
                f"My flight 6E-2041 (Delhi to Mumbai, Day 1, 08:00) {what}. As per your policy ({policy}), "
                f"please process a refund of {inr(f['price'])} to the original payment method.\n\n"
                f"PNR: {TRIP['pnr']}\nPassenger: {name}\n\nThank you,\n{name}")
    if kind == "hotel":
        if scn["type"] == "hotel" and o:
            return (f"Hello,\n\nRegarding my booking at Harbour View Inn: since the room was cancelled by the hotel, "
                    f"I have arranged {o['name']} instead. Please cancel the original booking and refund any "
                    f"prepaid amount of {inr(TRIP['bookings'][1]['price'])}.\n\nThanks,\n{name}")
        if o and o.get("arr") is not None:
            eta = hm(o["arr"] + 45)
        elif scn.get("delay"):
            eta = hm(f["arr"] + scn["delay"] + 45)
        else:
            eta = "later than planned"
        return (f"Hello Harbour View Inn,\n\nMy travel plans changed because of a flight "
                f"{'cancellation' if cancelled else 'delay'}. I now expect to reach the hotel around {eta} "
                f"instead of 14:00. Please hold my room and note a late check-in.\n\nThanks,\n{name}")
    if o and o.get("arr") is not None:
        eta = hm(o["arr"] + 60)
    elif scn.get("delay"):
        eta = hm(f["arr"] + scn["delay"] + 60)
    else:
        eta = "later"
    if scn["type"] == "hotel":
        where = f" to {o['name']} ({num(o['dist'])} km from the venue)" if o else ""
        return f"Hi,\n\nSmall change: my hotel has changed{where}. The 17:00 meeting is unaffected.\n\n{name}"
    return (f"Hi,\n\nMy flight to Mumbai was {'cancelled' if cancelled else 'delayed'}. I have rebooked and expect "
            f"to reach the city by {eta}. I will still make the 17:00 meeting.\n\n{name}")


def support_summary(scn_key, profile, ov):
    scn = get_scn(scn_key)
    c = cons(profile, ov, scn)
    ranked, removed = search_and_rank(scn, c)
    res = analyze(scn, c)
    affected = ", ".join(next(b["label"] for b in TRIP["bookings"] if b["id"] == i["id"])
                         for i in res["items"] if i["st"] != "ok") or "-"
    why = "\n".join(f" - {o['name']}: {o['why']}" for o in removed) or " - (no options evaluated)"
    return (f"SUPPORT HANDOFF\n\nTraveller: {profile.get('name', DEFAULTS['name'])} "
            f"({c['group']} traveller{'s' if c['group'] > 1 else ''})\nDisruption: {scn['title']}\n"
            f"Constraints: budget {inr(c['budget'])}, arrive by {c['arriveBy']}"
            f"{', no night travel' if c['noNight'] else ''}\nAgent tried: {len(removed) + len(ranked)} options.\n"
            f"Why nothing fit:\n{why}\n\nAffected bookings: {affected}\n"
            "Suggested next step: relax one rule (arrive-by or night travel) or move the meeting.")


def build_ics(option, ref, day):
    p = lambda n: f"{n:02d}"  # noqa: E731
    f = lambda m: f"{day}T{p((m // 60) % 24)}{p(m % 60)}00"  # noqa: E731
    return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//YatraSetu//EN", "BEGIN:VEVENT",
                        f"UID:{ref}@yatrasetu", f"DTSTAMP:{f(NOW)}", f"DTSTART:{f(option['dep'])}",
                        f"DTEND:{f(option['arr'])}", f"SUMMARY:{option['name']} DEL to BOM",
                        f"DESCRIPTION:Booking {ref} (sandbox)", "END:VEVENT", "END:VCALENDAR"])


# ---------------------------------------------------------------- help chatbot (reads from data, never guesses)

SUGGESTIONS = ["Why is option 1 ranked first?", "Will I get a refund?", "Change my budget to 9000",
               "Allow night travel", "What if the new flight is delayed?", "Talk to a human"]


def chat(message, scn_key, profile, ov):
    """Returns (reply, new_overrides, recovery_or_None)."""
    t = message.lower()
    ov = dict(ov or {})
    scn = get_scn(scn_key) if scn_key else None
    c = cons(profile, ov, scn)
    r = RULES["IndiGo"]
    f = TRIP["bookings"][0]

    if re.search(r"human|support|person|agent help", t):
        if scn:
            return ("Handing over to support with a summary so you do not repeat yourself:\n\n"
                    + support_summary(scn_key, profile, ov)), ov, None
        return ('No disruption is active, but I can hand you to support anytime. '
                'Use "Talk to support" once a recovery is running.'), ov, None

    if "budget" in t:
        m = re.search(r"(\d[\d,]{2,})", t)
        if not m:
            return ('Tell me the number, for example "change my budget to 9000". It applies to this trip only; '
                    'your saved default stays as is.'), ov, None
        v = int(m.group(1).replace(",", ""))
        if not scn:
            return ("No disruption is running. Change your default in Profile & defaults, "
                    "or trigger a scenario first."), ov, None
        ov["budget"] = v
        ov["hotelBudget"] = v
        rec = research(scn_key, profile, ov, f"Chat: budget for this trip set to {inr(v)}. Re-running search.")
        n = len(rec["ranked"])
        if n:
            return (f"Done. I re-ran the search with a budget of {inr(v)} for this trip. "
                    f"{n} option{'s pass' if n > 1 else ' passes'} now, and the top pick is "
                    f"{rec['ranked'][0]['name']}."), ov, rec
        return f"I re-ran it with {inr(v)}, but nothing passes your other rules yet.", ov, rec

    if "night" in t:
        if not scn:
            return ("Night travel is a hard rule in your profile. You can turn it off in Profile & defaults."), ov, None
        if re.search(r"allow|enable|ok|okay|include|turn off|disable", t):
            ov["noNight"] = False
            rec = research(scn_key, profile, ov, "Chat: night travel allowed for this trip. Re-running search.")
            n = len(rec["ranked"])
            return (f"Night travel is allowed for this trip only. {n} option{'' if n == 1 else 's'} pass now."), ov, rec
        return ('No night travel is one of your hard rules, so night options were removed. '
                'Say "allow night travel" and I will re-run the search for this trip.'), ov, None

    if re.search(r"refund|money back|compensat", t):
        if not scn:
            return f"Rules on file for IndiGo: cancellation → {r['cancel']}; delay → {r['delayRule']}.", ov, None
        if scn["type"] == "hotel":
            return ("The hotel cancelled your room, so you are entitled to a refund of "
                    + inr(TRIP["bookings"][1]["price"])
                    + ". I drafted the request. Open it from your checklist once you pick a new hotel."), ov, None
        if scn["status"] == "cancelled":
            return (f'Yes. IndiGo cancelled the flight, and its rule on file is "{r["cancel"]}". '
                    f"Your fare of {inr(f['price'])} is refundable. I drafted the claim for you."), ov, None
        h = num(scn["delay"] / 60)
        if scn["delay"] / 60 >= r["delayHours"]:
            return (f'Your delay is {h} h. IndiGo rule on file: "{r["delayRule"]}". '
                    "So you are eligible if you choose to cancel."), ov, None
        return (f"Your delay is {h} h, under IndiGo's {r['delayHours']} h threshold, "
                "so no refund unless it grows."), ov, None

    if re.search(r"why|rank|best|first|top", t):
        ranked, _ = search_and_rank(scn, c) if scn else ([], [])
        if not ranked:
            return "No ranking yet. Trigger a disruption first, or nothing passed your rules.", ov, None
        o = ranked[0]
        w = ranked[1] if len(ranked) > 1 else None
        s = o["sub"]
        txt = (f"{o['name']} scored {o['score']}/100: cost {jsround(s['cost'] * 100)}, time {jsround(s['time'] * 100)}, "
               f"comfort {jsround(s['comfort'] * 100)}, availability {jsround(s['risk'] * 100)}. ")
        if w:
            txt += f"The runner-up, {w['name']}, scored {w['score']}. "
        txt += (f"Weights come from your profile (cost {c['wCost']}, time {c['wTime']}, comfort {c['wComfort']}, "
                f"availability {c['wRisk']}). Scoring is plain code, so these numbers are exact.")
        return txt, ov, None

    if re.search(r"delay|again|track|cancel.*again|what if", t):
        return ("After you confirm, I keep watching the new journey. If it is delayed or cancelled too, I restart "
                "the same flow, alert you, and release or roll back anything that no longer fits."), ov, None
    if re.search(r"hotel|check.?in", t):
        if scn:
            return 'I drafted a hotel message. Open "View draft" from your checklist after you approve a plan.', ov, None
        return ("Your hotel check-in is 14:00 at Harbour View Inn. If your arrival slips, "
                "I draft a late check-in note for you."), ov, None
    if re.search(r"privacy|data|ai |secure|safe|consent", t):
        return ("The AI only sees masked data (traveller 1, budget, times, prices). Your ID, phone and payment "
                "details never leave your profile, and you can delete your data anytime in Profile & defaults."), ov, None
    if re.search(r"profile|default|setting", t):
        return ('Open "Profile & defaults" at the top right to change your budget, deadline, night-travel rule, mode '
                'and ranking weights. Trip-level changes (like "budget 9000") never alter your saved defaults.'), ov, None
    if re.search(r"book|pay|ticket", t):
        return ("In this prototype booking is a sandbox, so no real ticket or money is involved. In production we "
                "would use partner booking APIs, or hand off to the provider page with details pre-filled."), ov, None
    return ("I can explain a ranking, check refund rules, change this trip's budget, allow night travel, draft "
            "messages, or hand you to support. Try one of the suggestions below."), ov, None
