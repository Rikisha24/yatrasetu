"""Mock travel data. Clearly mock: production swaps in airline/NDC, rail and hotel APIs."""

NOW = 390  # 06:30, the moment the disruption is detected

TRIP = {
    "pnr": "7QX2LM",
    "bookings": [
        {"id": "F1", "type": "flight", "icon": "✈️", "label": "IndiGo 6E-2041", "sub": "Day 1 · DEL → BOM",
         "dep": 480, "arr": 610, "price": 5200, "airline": "IndiGo"},
        {"id": "H1", "type": "hotel", "icon": "🏨", "label": "Harbour View Inn, Bandra",
         "sub": "Day 1 · check-in 14:00", "checkin": 840, "price": 5800},
        {"id": "M1", "type": "meeting", "icon": "📅", "label": "Client meeting · BKC",
         "sub": "Day 1 · 17:00", "at": 1020},
        {"id": "F2", "type": "flight", "icon": "✈️", "label": "Air India AI-632",
         "sub": "Day 2 · BOM → DEL 19:00", "price": 4900},
    ],
}

TRANSPORT = [
    {"id": "O1", "mode": "flight", "name": "Air India AI-665", "note": "Direct", "dep": 570, "arr": 705, "price": 6400, "seats": 9, "comfort": 4},
    {"id": "O2", "mode": "flight", "name": "IndiGo 6E-2043", "note": "Direct", "dep": 640, "arr": 770, "price": 5900, "seats": 4, "comfort": 3},
    {"id": "O3", "mode": "flight", "name": "Air India AI-887", "note": "Direct · meal included", "dep": 735, "arr": 860, "price": 7800, "seats": 12, "comfort": 5},
    {"id": "O4", "mode": "flight", "name": "Akasa QP-1102", "note": "Direct", "dep": 810, "arr": 940, "price": 4900, "seats": 2, "comfort": 3},
    {"id": "O5", "mode": "flight", "name": "SpiceJet SG-8719", "note": "Direct · last seat", "dep": 470, "arr": 600, "price": 6700, "seats": 1, "comfort": 2},
    {"id": "O6", "mode": "multi", "name": "IndiGo 6E-5120 via Ahmedabad", "note": "1 stop · 55 min layover", "dep": 545, "arr": 850, "price": 4600, "seats": 6, "comfort": 2},
    {"id": "O7", "mode": "multi", "name": "Flight to Pune + cab to Mumbai", "note": "AI-871 then pre-booked cab (3 h)", "dep": 530, "arr": 870, "price": 5100, "seats": 5, "comfort": 2},
    {"id": "O8", "mode": "train", "name": "12951 Rajdhani Express", "note": "3A · arrives next morning", "dep": 1015, "arr": 1935, "price": 3300, "seats": 20, "comfort": 4},
    {"id": "O9", "mode": "bus", "name": "Overnight sleeper bus", "note": "Sleeper", "dep": 1350, "arr": 2160, "price": 2200, "seats": 15, "comfort": 1},
    {"id": "O10", "mode": "flight", "name": "Akasa QP-1100", "note": "Direct", "dep": 420, "arr": 550, "price": 5500, "seats": 7, "comfort": 3},
]

HOTELS = [
    {"id": "HA", "name": "Bandra Bay Suites", "price": 6200, "dist": 4.2, "rating": 4.3, "freeCancel": True},
    {"id": "HB", "name": "BKC Business Stay", "price": 7400, "dist": 1.1, "rating": 4.5, "freeCancel": True},
    {"id": "HC", "name": "Linking Road Inn", "price": 4300, "dist": 5.0, "rating": 3.8, "freeCancel": False},
    {"id": "HD", "name": "Juhu Seaside Hotel", "price": 5600, "dist": 11.5, "rating": 4.1, "freeCancel": True},
    {"id": "HE", "name": "Kurla Transit Lodge", "price": 3200, "dist": 3.0, "rating": 3.4, "freeCancel": True},
]

# Refund / rebooking rules live in data, never in the LLM.
RULES = {"IndiGo": {"cancel": "Full refund or free rebooking", "delayHours": 3,
                    "delayRule": "Refund on request if delay is 3 h or more"}}

SCENARIOS = {
    "cancel": {"label": "Flight cancelled", "status": "cancelled", "type": "flight",
               "title": "IndiGo 6E-2041 was cancelled by the airline"},
    "delay4": {"label": "Flight delayed 4 h (agent keeps plan)", "status": "delayed", "delay": 240, "type": "flight",
               "title": "IndiGo 6E-2041 is delayed by 4 hours"},
    "delay7": {"label": "Flight delayed 7 h", "status": "delayed", "delay": 420, "type": "flight",
               "title": "IndiGo 6E-2041 is delayed by 7 hours"},
    "group": {"label": "Flight cancelled · family of 4", "status": "cancelled", "type": "flight", "group": 4,
              "title": "IndiGo 6E-2041 was cancelled — 4 travellers affected"},
    "shutdown": {"label": "Mumbai airport closed (nothing fits)", "status": "cancelled", "type": "flight", "flightsDown": True,
                 "title": "IndiGo 6E-2041 cancelled — Mumbai airport closed by weather"},
    "hotel": {"label": "Hotel overbooked", "type": "hotel",
              "title": "Harbour View Inn cancelled your room (overbooked)"},
}

DEFAULTS = {"name": "Priya Sharma", "budget": 7000, "hotelBudget": 6500, "arriveBy": "15:00", "noNight": True,
            "mode": "any", "group": 1, "wCost": 25, "wTime": 40, "wComfort": 25, "wRisk": 10, "consent": True}
