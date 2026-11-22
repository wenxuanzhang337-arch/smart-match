"""
Smart Match - AI teammate recommender for HKUST group projects.
Prototype v7: intro screen -> questionnaire -> MATCH FOUND -> teammates.
n+3 shortlist with an interactive team-builder (live coverage radar),
50-sample browseable library with dimension filters.

Run with:  streamlit run app.py
"""
import math
import random
import streamlit as st
import requests

# ---------------------------------------------------------------------------
# The matching rubric (grounded in team-effectiveness research):
#   D1 Roles / skills  -> complementarity  (a team needs DIFFERENT skills)
#   D2 Availability    -> alignment        (overlapping meeting times, hours)
#   D3 Working style   -> compatibility    (similar styles cooperate better)
#   D4 Goals           -> alignment        (same target grade + expectations)
# Weights: 30 / 25 / 25 / 20
# ---------------------------------------------------------------------------

ALL_ROLES = [
    "Programming / technical implementation",
    "Report / essay writing",
    "Presentation / public speaking",
    "Project planning / progress management",
    "Data collection and analysis",
    "Design / visualization / slides",
    "Coordination / team leader",
]

RADAR_AXES = ["Code", "Writing", "Speaking", "Planning", "Data", "Design", "Leadership"]

HOURS = ["<2h", "2-5h", "5-10h", ">10h"]
GRADES = ["Aim for the highest (A/A+)", "A good grade (B+/A-)", "Just pass", "Doesn't matter"]
EXPECT = ["Same effort as me", "More committed is better", "Just don't drag me down", "Doesn't matter"]
MEETING = ["Weekday daytime", "Weekday evening", "Weekend daytime", "Weekend evening"]
LOAD = ["Internship", "Part-time job", "Job-hunting", "Graduate-school applications", "None of the above"]
DISCUSSION = ["Listen first, then speak", "Think out loud", "Come prepared", "Mostly listen"]
DECISION = ["Leader decides", "Group vote", "Owner decides", "Consensus"]
DEADLINE = ["Start early", "Start early with a buffer", "Last 1-2 weeks", "Last few days", "Depends"]
RELIABILITY = ["On time, every time", "Mostly on time", "Sometimes needed a reminder", "Varied a lot"]
TEAM_SIZES = ["2", "3", "4", "5", "6"]

# Shortlist = required team size + this many extra candidates, so users can weigh options.
EXTRA_CANDIDATES = 3


# ---------------------------------------------------------------------------
# Sample library generator. 50 deterministic, diverse, fictional profiles.
# Emails / majors / years / stats are fictional for the prototype.
# ---------------------------------------------------------------------------
_FIRST = ["Alex", "Bea", "Chris", "Dana", "Eli", "Fay", "Gia", "Hal", "Ivy", "Jay",
          "Kai", "Leo", "Mia", "Nia", "Omar", "Pia", "Quin", "Rhea", "Sam", "Tia",
          "Uma", "Van", "Wen", "Xiu", "Yuna", "Zane", "Ada", "Ben", "Coco", "Devi",
          "Ewan", "Finn", "Greta", "Hugo", "Ines", "Juno", "Kira", "Lian", "Miro", "Nina",
          "Otis", "Petra", "Remy", "Sora", "Theo", "Ula", "Vero", "Wren", "Xian", "Yara", "Ziv"]
_LAST = ["Wong", "Chan", "Lee", "Ng", "Tan", "Lim", "Cheng", "Ho", "Lau", "Chow",
         "Fung", "Kwok", "Yip", "Tsang", "Tang", "Cheung", "Lam", "Kwan", "Hui", "Lo",
         "Mak", "Mok", "Or", "Poon", "Siu", "To", "Tse", "Wan", "Wu", "Yam",
         "Yau", "Yu", "Au", "Chiu", "Fong", "Hau", "Ip", "Kong", "Leung", "Ma",
         "Ngai", "So", "Tam", "Yim", "Yun"]
# HKUST undergraduate major programs (official abbreviations in parentheses).
_MAJORS = [
    "Aerospace Engineering (AE)",
    "Biochemistry and Cell Biology (BCB)",
    "Bioengineering (BIEN)",
    "Biotechnology (BIOT)",
    "Biotechnology and Business (BIBU)",
    "Chemical and Environmental Engineering (CEEV)",
    "Chemistry (CHEM)",
    "Civil and Environmental Engineering (CIVL)",
    "Computer Engineering (CPEG)",
    "Computer Science (COMP)",
    "Data Science and Technology (DSCT)",
    "Decision Analytics (DA)",
    "Economics (ECON)",
    "Economics and Finance (ECOF)",
    "Electronic Engineering (ELEC)",
    "Environmental Management and Technology (EVMT)",
    "Finance (FINA)",
    "General Business Management (GBM)",
    "Global Business (GBUS)",
    "Global China Studies (GCST)",
    "Individualized Interdisciplinary Major (IIM)",
    "Industrial Engineering and Engineering Management (IEEM)",
    "Information Systems (IS)",
    "Integrative Systems and Design (ISD)",
    "Management (MGMT)",
    "Marketing (MARK)",
    "Mathematics (MATH)",
    "Mathematics and Economics (MAEC)",
    "Mechanical Engineering (MECH)",
    "Ocean Science and Technology (OCES)",
    "Operations Management (OM)",
    "Physics (PHYS)",
    "Professional Accounting (PACC)",
    "Quantitative Finance (QFIN)",
    "Quantitative Social Analysis (QSA)",
    "Risk Management and Business Intelligence (RMBI)",
    "Sustainable and Green Finance (SGFN)",
    "Sustainable Energy Engineering (SUSEE)",
]
_OTHER_COURSES = ["ISOM3540", "COMP2011", "COMP1021", "MARK2120", "ECON2103", "ACCT2010", "LANG1002", "PHYS1112"]

_ROLE_STAT_BONUS = {
    "Programming / technical implementation": {"Code": 22},
    "Report / essay writing": {"Writing": 22},
    "Presentation / public speaking": {"Speaking": 22},
    "Project planning / progress management": {"Planning": 22},
    "Data collection and analysis": {"Data": 22},
    "Design / visualization / slides": {"Design": 22},
    "Coordination / team leader": {"Leadership": 22},
}


def build_sample_library(n=50, seed=7):
    rng = random.Random(seed)
    students = []
    seen_names = set()
    seen_emails = set()
    guard = 0
    while len(students) < n and guard < 5000:
        guard += 1
        fn, ln = rng.choice(_FIRST), rng.choice(_LAST)
        name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}@connect.ust.hk"
        if name in seen_names or email in seen_emails:
            continue
        seen_names.add(name)
        seen_emails.add(email)

        roles = rng.sample(ALL_ROLES, rng.choice([1, 2, 2, 3]))
        stats = {axis: rng.randint(42, 78) for axis in RADAR_AXES}
        for r in roles:
            for axis, bonus in _ROLE_STAT_BONUS[r].items():
                stats[axis] = min(95, stats[axis] + bonus)

        busy = ["Internship", "Part-time job", "Job-hunting", "Graduate-school applications"]
        load = ["None of the above"] if rng.random() < 0.4 else rng.sample(busy, rng.randint(1, 2))
        course = "COMP1945" if rng.random() < 0.62 else rng.choice(_OTHER_COURSES)

        students.append({
            "name": name, "email": email, "major": rng.choice(_MAJORS),
            "year": rng.choice(["Year 1", "Year 2", "Year 3", "Year 4"]),
            "course": course, "roles": roles,
            "hours": rng.choice(HOURS),
            "meeting": rng.sample(MEETING, rng.randint(1, 3)),
            "load": load,
            "grade": rng.choice(GRADES), "expect": rng.choice(EXPECT),
            "discussion": rng.choice(DISCUSSION), "decision": rng.choice(DECISION),
            "deadline": rng.choice(DEADLINE), "reliability": rng.choice(RELIABILITY),
            "stats": stats,
        })
    return students


MOCK_STUDENTS = build_sample_library()


# ---------------------------------------------------------------------------
# Anonymized respondent storage (Supabase free tier). If unconfigured, matching
# and the library fall back to the in-memory sample library and the app still runs.
# ---------------------------------------------------------------------------
RESPONDENT_TABLE = "respondents"


def _supabase_headers():
    key = st.secrets.get("SUPABASE_ANON_KEY", "")
    headers = {"apikey": key, "Content-Type": "application/json"}
    # New-format keys (sb_publishable_/sb_secret_) are opaque, not JWTs — they must
    # only go in the `apikey` header. Legacy anon keys are JWTs and also use Authorization.
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _supabase_url():
    base = st.secrets.get("SUPABASE_URL", "").strip().rstrip("/")
    return f"{base}/rest/v1/{RESPONDENT_TABLE}" if base else ""


def fetch_respondents():
    """Read all anonymized respondents from Supabase ([] if unconfigured / offline)."""
    url = _supabase_url()
    if not url or not st.secrets.get("SUPABASE_ANON_KEY", ""):
        return []
    try:
        r = requests.get(f"{url}?select=*", headers=_supabase_headers(), timeout=15)
        if r.status_code != 200:
            return []
        return [{
            "name": row.get("name"), "email": row.get("email"),
            "major": row.get("major"), "year": row.get("year"),
            "course": row.get("course"), "roles": row.get("roles") or [],
            "hours": row.get("hours"), "meeting": row.get("meeting") or [],
            "load": row.get("load") or [], "grade": row.get("grade"),
            "expect": row.get("expect"), "discussion": row.get("discussion"),
            "decision": row.get("decision"), "deadline": row.get("deadline"),
            "reliability": row.get("reliability"), "stats": row.get("stats") or {},
        } for row in r.json()]
    except Exception:
        return []


def save_respondent(profile):
    """Insert one anonymized profile into Supabase. Returns True on success."""
    url = _supabase_url()
    if not url or not st.secrets.get("SUPABASE_ANON_KEY", ""):
        return False
    try:
        r = requests.post(url, headers={**_supabase_headers(), "Prefer": "return=minimal"},
                          json=profile, timeout=15)
        return r.status_code in (200, 201, 204)
    except Exception:
        return False


@st.cache_data(ttl=600, show_spinner=False)
def candidate_pool():
    """Mock library + all anonymized respondents, used for matching and browsing."""
    return MOCK_STUDENTS + fetch_respondents()


def make_anonymized_profile(user, major):
    """Turn a questionnaire submission into an anonymized candidate profile."""
    pool = candidate_pool()
    taken_names = {s["name"] for s in pool}
    taken_emails = {s["email"] for s in pool}
    rng = random.Random()
    name = email = None
    for _ in range(200):
        fn, ln = rng.choice(_FIRST), rng.choice(_LAST)
        cname = f"{fn} {ln}"
        cemail = f"{fn.lower()}.{ln.lower()}@connect.ust.hk"
        if cname not in taken_names and cemail not in taken_emails:
            name, email = cname, cemail
            break
    if name is None:
        n = len(pool) + 1
        name, email = f"Student {n}", f"student{n}@connect.ust.hk"
    stats = {axis: rng.randint(42, 78) for axis in RADAR_AXES}
    for r in user["roles"]:
        for axis, bonus in _ROLE_STAT_BONUS.get(r, {}).items():
            stats[axis] = min(95, stats[axis] + bonus)
    return {
        "name": name, "email": email, "major": major, "year": user.get("year"),
        "course": user["course"], "roles": list(user["roles"]),
        "hours": user["hours"], "meeting": list(user["meeting"]), "load": list(user["load"]),
        "grade": user["grade"], "expect": user["expect"],
        "discussion": user["discussion"], "decision": user["decision"],
        "deadline": user["deadline"], "reliability": user["reliability"],
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------
def floating_particles(n_dust=30, n_ember=9):
    """Return fixed-position particles that float up the screen."""
    parts = []
    for _ in range(n_dust):
        left = random.uniform(0, 100)
        size = random.uniform(2, 4)
        dur = random.uniform(10, 22)
        delay = random.uniform(0, 22)
        op = random.uniform(0.15, 0.5)
        parts.append(
            f'<span class="sm-dot" style="left:{left:.1f}%;width:{size:.1f}px;'
            f'height:{size:.1f}px;animation-duration:{dur:.1f}s;'
            f'animation-delay:-{delay:.1f}s;opacity:{op:.2f};"></span>'
        )
    for _ in range(n_ember):
        left = random.uniform(0, 100)
        size = random.uniform(5, 9)
        dur = random.uniform(14, 30)
        delay = random.uniform(0, 30)
        op = random.uniform(0.2, 0.55)
        parts.append(
            f'<span class="sm-ember" style="left:{left:.1f}%;width:{size:.1f}px;'
            f'height:{size:.1f}px;animation-duration:{dur:.1f}s;'
            f'animation-delay:-{delay:.1f}s;opacity:{op:.2f};"></span>'
        )
    return "".join(parts)


def starfield(n=70):
    """Return fixed-position twinkling stars for background depth."""
    stars = []
    for _ in range(n):
        left = random.uniform(0, 100)
        top = random.uniform(0, 100)
        size = random.uniform(1, 2.6)
        dur = random.uniform(2, 6)
        delay = random.uniform(0, 6)
        stars.append(
            f'<span class="sm-star" style="left:{left:.1f}%;top:{top:.1f}%;'
            f'width:{size:.1f}px;height:{size:.1f}px;'
            f'animation-duration:{dur:.1f}s;animation-delay:-{delay:.1f}s;"></span>'
        )
    return "".join(stars)


def match_overlay():
    """Full-screen 'MATCH FOUND' corner-bracket transition."""
    return (
        '<div class="sm-overlay"><div class="sm-frame">'
        '<span class="c tl"></span><span class="c tr"></span><span class="c bl"></span><span class="c br"></span>'
        '<div class="sm-overlay-text">MATCH FOUND</div>'
        '<div class="sm-overlay-sub">Teammate view ready</div>'
        '</div></div>'
    )


def launch_overlay():
    """Full-screen 'MATCH START' corner-bracket transition."""
    return (
        '<div class="sm-launch"><div class="sm-launch-center"><div class="sm-frame">'
        '<span class="c tl"></span><span class="c tr"></span><span class="c bl"></span><span class="c br"></span>'
        '<div class="sm-launch-text">MATCH START</div>'
        '<div class="sm-launch-sub">Preparing your questionnaire</div>'
        '</div></div></div>'
    )


def section(num, title):
    """Arknights-style section header: big number + title + fading rule."""
    return (f'<div class="sm-section"><span class="sm-sec-num">{num}</span>'
            f'<span class="sm-sec-title">{title}</span>'
            f'<span class="sm-sec-line"></span></div>')


def intro_hero():
    """Geometric 'registration target' title screen."""
    return (
        '<div class="sm-hero">'
        '<div class="sm-target"><div class="t1"></div><div class="t2"></div><div class="t3"></div></div>'
        '<div class="sm-hero-title">FIND YOUR <span class="accent">TEAM</span></div>'
        '<div class="sm-tagline">One short questionnaire. Matches scored across five dimensions.</div>'
        '<div class="sm-chips">'
        '<span class="sm-chip">TOPSIS RANKING</span>'
        '<span class="sm-chip">GREEDY TEAMING</span>'
        '<span class="sm-chip">AI ANALYSIS</span>'
        '</div>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
def ordinal_score(a, b, options):
    """0..1 similarity between two choices from an ordered list (closer = higher)."""
    if a == b:
        return 1.0
    dist = abs(options.index(a) - options.index(b))
    span = len(options) - 1
    return max(0.0, 1.0 - dist / span)


DEFAULT_WEIGHTS = {
    "Skills": 25, "Availability": 20, "Working style": 20, "Goals": 15, "Reliability": 20,
}


def score_roles(user, cand):
    """Complementarity: do they cover roles I lack, without merely duplicating what I already do?"""
    my = set(user["roles"])
    their = set(cand["roles"])
    if not their:
        return 0.0
    brings = their - my
    overlap = their & my
    novelty = len(brings) / len(their)
    duplication = len(overlap) / len(their)
    return max(0.0, novelty - 0.5 * duplication)


def score_availability(user, cand):
    u, c = set(user["meeting"]), set(cand["meeting"])
    time_score = len(u & c) / max(len(u | c), 1)
    hours_score = ordinal_score(user["hours"], cand["hours"], HOURS)
    heavy = {"Internship", "Part-time job", "Job-hunting"}
    load_penalty = 0.1 if (set(cand["load"]) & heavy) else 0.0
    return max(0.0, 0.6 * time_score + 0.4 * hours_score - load_penalty)


def score_style(user, cand):
    d_disc = 1.0 if user["discussion"] == cand["discussion"] else 0.0
    d_dec = 1.0 if user["decision"] == cand["decision"] else 0.0
    d_dead = ordinal_score(user["deadline"], cand["deadline"], DEADLINE)
    return (d_disc + d_dec + d_dead) / 3.0


def score_goals(user, cand):
    g = ordinal_score(user["grade"], cand["grade"], GRADES)
    e = 1.0 if user["expect"] == cand["expect"] else 0.5
    return 0.5 * g + 0.5 * e


def score_reliability(user, cand):
    return ordinal_score(user["reliability"], cand["reliability"], RELIABILITY)


def topsis_closeness(rows, weights):
    """TOPSIS multi-criteria ranking (Hwang & Yoon, 1981).

    rows: list of {criterion: value} (0..1, all benefit-type).
    weights: {criterion: w} normalized to sum 1.
    Returns a closeness score (0..1) per row, in the same order.
    """
    keys = list(weights.keys())
    n = len(rows)
    if n == 0:
        return []
    # vector normalization per criterion
    norms = []
    for j, k in enumerate(keys):
        s = sum(r[k] ** 2 for r in rows) ** 0.5
        norms.append(s if s > 0 else 1.0)
    # weighted normalized decision matrix
    v = [[(rows[i][k] / norms[j]) * weights[k] for j, k in enumerate(keys)] for i in range(n)]
    ideal_best = [max(v[i][j] for i in range(n)) for j in range(len(keys))]
    ideal_worst = [min(v[i][j] for i in range(n)) for j in range(len(keys))]
    closeness = []
    for i in range(n):
        sp = sum((v[i][j] - ideal_best[j]) ** 2 for j in range(len(keys))) ** 0.5
        sm = sum((v[i][j] - ideal_worst[j]) ** 2 for j in range(len(keys))) ** 0.5
        closeness.append(sm / (sp + sm) if (sp + sm) else 0.0)
    return closeness


def greedy_team(pool, need):
    """Greedy team assembly: repeatedly add the candidate that most increases the
    team's cumulative skill coverage across the 7 radar axes (submodular max-coverage)."""
    team = []
    remaining = list(pool)
    covered = {axis: 0.0 for axis in RADAR_AXES}
    for _ in range(need):
        best, best_gain = None, 0.0
        for cand in remaining:
            gain = sum(max(0.0, cand["stats"][axis] - covered[axis]) for axis in RADAR_AXES)
            if gain > best_gain:
                best_gain, best = gain, cand
        if best is None:
            break
        team.append(best)
        remaining.remove(best)
        for axis in RADAR_AXES:
            covered[axis] = max(covered[axis], best["stats"][axis])
    return team


def match(user):
    weights = user.get("weights") or DEFAULT_WEIGHTS
    if not any(weights.values()):
        weights = dict(DEFAULT_WEIGHTS)  # all-zero = no preference; fall back to balanced
    wsum = sum(weights.values()) or 1.0
    rows = []
    for cand in candidate_pool():
        if cand["course"] != user["course"]:
            continue
        rows.append((cand, {
            "Skills": score_roles(user, cand),
            "Availability": score_availability(user, cand),
            "Working style": score_style(user, cand),
            "Goals": score_goals(user, cand),
            "Reliability": score_reliability(user, cand),
        }))
    norm_w = {k: weights[k] / wsum for k in weights}
    closeness = topsis_closeness([d for _, d in rows], norm_w)
    results = []
    for (cand, d), c in zip(rows, closeness):
        breakdown = {f"{k} ({round(100 * norm_w[k])}%)": v for k, v in d.items()}
        results.append((c, cand, breakdown))
    results.sort(key=lambda r: r[0], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Radar chart + analysis
# ---------------------------------------------------------------------------
def radar_svg(stats, size=300):
    cx = cy = size / 2
    r = size * 0.34
    label_r = size * 0.46
    n = len(RADAR_AXES)

    def vertex(radius, i, frac=1.0):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        return (cx + radius * frac * math.cos(ang), cy + radius * frac * math.sin(ang))

    parts = []
    for level in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{vertex(r, i, level)[0]:.1f},{vertex(r, i, level)[1]:.1f}" for i in range(n))
        parts.append(f'<polygon points="{pts}" fill="none" stroke="#232329" stroke-width="1"/>')
    for i in range(n):
        x, y = vertex(r, i)
        parts.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="#232329" stroke-width="1"/>')

    data_pts = " ".join(
        f"{vertex(r, i, stats[RADAR_AXES[i]] / 100)[0]:.1f},{vertex(r, i, stats[RADAR_AXES[i]] / 100)[1]:.1f}"
        for i in range(n))
    parts.append(f'<polygon points="{data_pts}" fill="rgba(125,155,198,0.26)" stroke="#7d9bc6" stroke-width="2"/>')
    for i in range(n):
        x, y = vertex(r, i, stats[RADAR_AXES[i]] / 100)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#7d9bc6"/>')

    for i, label in enumerate(RADAR_AXES):
        lx, ly = vertex(label_r, i)
        anchor = "middle"
        if lx > cx + 6:
            anchor = "start"
        elif lx < cx - 6:
            anchor = "end"
        parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#9a9aa3" font-size="10" font-family="IBM Plex Mono, monospace" '
                     f'text-anchor="{anchor}" dominant-baseline="middle">{label}</text>')

    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">' + "".join(parts) + '</svg>'


PROJECT_CONTEXT = (
    "PROJECT BACKGROUND: Smart Match is an AI-powered teammate-recommendation system for HKUST "
    "(Hong Kong University of Science and Technology) students forming groups for course projects. "
    "A student fills a short questionnaire and sets personal priority weights; the system scores every candidate "
    "in the sample library on five research-grounded dimensions — (1) Roles & skills complementarity (default 25%): "
    "a team needs different, non-overlapping skills; (2) Availability alignment (20%): overlapping meeting times and "
    "similar weekly commitment; (3) Working-style compatibility (20%): similar discussion, decision and deadline habits; "
    "(4) Goals alignment (15%): same target grade and effort expectations; (5) Reliability (20%): the candidate's "
    "track record of delivering on time. Candidates are ranked with TOPSIS multi-criteria decision analysis, and a "
    "greedy team-assembly step then selects teammates that maximize collective skill coverage across seven ability "
    "areas. Candidates outside the student's course are excluded, and the top candidates are recommended so the "
    "student can assemble a balanced team."
)


def _analysis_prompt(user, cand, total):
    abilities = ", ".join(f"{a}={cand['stats'][a]}" for a in RADAR_AXES)
    weights = user.get("weights") or DEFAULT_WEIGHTS
    wsum = sum(weights.values()) or 1.0
    w_str = ", ".join(f"{k}={round(100 * weights[k] / wsum)}%" for k in weights)
    return (
        PROJECT_CONTEXT + "\n\n"
        "YOUR TASK: Write 3-4 sentences (plain text, no markdown, no headings) explaining why this specific "
        "candidate fits this student. Reference the five dimensions above where relevant. "
        "Cover: which skills the candidate adds that the student lacks, working-style compatibility, "
        "availability overlap, goal alignment, and reliability. Be specific and factual. Do NOT write a verdict sentence.\n\n"
        f"STUDENT — course: {user['course']}; roles: {', '.join(user['roles'])}; "
        f"discussion: {user['discussion']}; decision: {user['decision']}; deadline: {user['deadline']}; "
        f"reliability: {user['reliability']}; priority weights: {w_str}.\n"
        f"CANDIDATE {cand['name']} ({cand['major']}, {cand['year']}) — roles: {', '.join(cand['roles'])}; "
        f"abilities 0-100: {abilities}; "
        f"discussion: {cand['discussion']}; decision: {cand['decision']}; deadline: {cand['deadline']}; "
        f"reliability: {cand['reliability']}; "
        f"availability: {cand['hours']}/week, meets {', '.join(cand['meeting'])}, load {', '.join(cand['load'])}; "
        f"goal: {cand['grade']}, expects {cand['expect']}.\n"
        f"Match score: {total*100:.0f}%."
    )


@st.cache_data(ttl=1800, show_spinner=False)
def llm_analysis(prompt):
    """Return a DeepSeek-generated analysis string, or None on failure / no key."""
    try:
        key = st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        return None
    if not key:
        return None
    try:
        import requests
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": st.secrets.get("DEEPSEEK_MODEL", "deepseek-chat"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def analysis_html(user, cand, total):
    llm_text = llm_analysis(_analysis_prompt(user, cand, total))
    if total >= 0.7:
        verdict = "Verdict: high match — contact first."
    elif total >= 0.5:
        verdict = "Verdict: solid match — keep on the shortlist."
    else:
        verdict = "Verdict: moderate match — review before committing."

    if llm_text:
        safe = llm_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        body = f"<p>{safe}</p>"
        tag = ' <span class="sm-ai-tag">DeepSeek</span>'
    else:
        my, their = set(user["roles"]), set(cand["roles"])
        brings = their - my
        overlap = their & my
        bullets = []
        if brings:
            bullets.append(f"<p><b>Complements you</b> with {', '.join(sorted(brings))} — skills your profile is missing.</p>")
        if overlap:
            bullets.append(f"<p><b>Overlaps you</b> on {', '.join(sorted(overlap))}; if you team up, split these tasks explicitly.</p>")
        bullets.append(f"<p><b>Working style:</b> {cand['discussion']} in discussion &middot; "
                       f"{cand['decision']} on decisions &middot; {cand['deadline']} on deadlines.</p>")
        bullets.append(f"<p><b>Availability:</b> {cand['hours']}/week &middot; meets {', '.join(cand['meeting'])} "
                       f"&middot; outside load: {', '.join(cand['load'])}.</p>")
        bullets.append(f"<p><b>Goal:</b> {cand['grade']} &middot; expects teammates who {cand['expect'].lower()}.</p>")
        body = "".join(bullets)
        tag = ""

    return ('<div class="sm-analysis"><div class="sm-analysis-title">AI Analysis' + tag + '</div>'
            + body + f'<p class="sm-verdict">{verdict}</p></div>')


def team_coverage_html(cands):
    """Combined coverage radar + score + gap warnings for the selected team."""
    if not cands:
        return ('<div class="sm-coverage"><div class="sm-coverage-title">Team Coverage</div>'
                '<div class="sm-gap">Select at least one teammate above to see the combined skill coverage.</div></div>')
    max_stats = {axis: max(c["stats"][axis] for c in cands) for axis in RADAR_AXES}
    coverage = round(sum(max_stats.values()) / len(RADAR_AXES))
    gaps = [a for a in RADAR_AXES if max_stats[a] < 60]
    bars = "".join(
        f'<div class="sm-bar"><span class="sm-bar-label">{a}</span>'
        f'<span class="sm-bar-track"><span class="sm-bar-fill" style="width:{max_stats[a]}%"></span></span>'
        f'<span class="sm-bar-val">{max_stats[a]}</span></div>'
        for a in RADAR_AXES)
    if gaps:
        gap_html = ('<div class="sm-gap"><b>Coverage gap:</b> no one on this team is strong in '
                    + ", ".join(gaps) + '. Consider recruiting for it.</div>')
    else:
        gap_html = '<div class="sm-gap ok">All seven dimensions are covered by someone strong.</div>'
    return (
        '<div class="sm-coverage">'
        f'<div class="sm-coverage-title">Team Coverage <span class="sm-cover-score">{coverage} / 100</span></div>'
        '<div class="sm-detail-grid">'
        f'<div class="sm-radar">{radar_svg(max_stats)}</div>'
        f'<div class="sm-detail-right">{bars}{gap_html}</div>'
        '</div></div>'
    )


def render_results(shortlist, user, team_size, picked_set):
    """Render the n+3 shortlist as clickable cards; picked ones are highlighted."""
    need = team_size - 1
    head = (f'<div class="sm-results-head">Team of {team_size} &middot; '
            f'{len(shortlist)} candidates shortlisted &middot; pick {need}</div>')
    cards = []
    for i, (total, cand, breakdown) in enumerate(shortlist, 1):
        picked = cand["name"] in picked_set
        badge = '<span class="sm-picked-badge">SELECTED</span>' if picked else ''
        card_cls = "sm-card picked" if picked else "sm-card"
        bars = []
        for label, val in breakdown.items():
            bars.append(
                '<div class="sm-bar">'
                f'<span class="sm-bar-label">{label}</span>'
                '<span class="sm-bar-track">'
                f'<span class="sm-bar-fill" style="width:{val*100:.0f}%"></span>'
                '</span>'
                f'<span class="sm-bar-val">{val*100:.0f}%</span>'
                '</div>'
            )
        bars_html = "".join(bars)
        radar = radar_svg(cand["stats"])
        analysis = analysis_html(user, cand, total)
        cards.append(
            f'<details class="{card_cls}" style="animation-delay:{0.1 * (i - 1):.2f}s">'
            f'<summary class="sm-card-head">'
            f'<span class="sm-rank">#{i}</span>'
            f'<span class="sm-name">{cand["name"]}</span>'
            f'<span class="sm-major">{cand["major"]}</span>'
            f'{badge}'
            f'<span class="sm-score">{total*100:.0f}%</span>'
            '</summary>'
            '<div class="sm-detail">'
            f'<div class="sm-meta"><a class="sm-mail" href="mailto:{cand["email"]}">{cand["email"]}</a>'
            f' &middot; {cand["major"]} &middot; {cand["year"]}</div>'
            '<div class="sm-detail-grid">'
            f'<div class="sm-radar">{radar}</div>'
            f'<div class="sm-detail-right">{bars_html}{analysis}</div>'
            '</div></div></details>'
        )
    st.markdown(head + "".join(cards), unsafe_allow_html=True)


def stat_bars(s):
    bars = []
    for axis in RADAR_AXES:
        v = s["stats"][axis]
        bars.append(
            '<div class="sm-bar">'
            f'<span class="sm-bar-label">{axis}</span>'
            '<span class="sm-bar-track"><span class="sm-bar-fill" style="width:{v}%"></span></span>'
            f'<span class="sm-bar-val">{v}</span>'
            '</div>'
        )
    return '<div class="sm-stats">' + "".join(bars) + '</div>'


def render_library_cards(students):
    if not students:
        st.markdown('<div class="sm-note">No profiles match the current filters.</div>', unsafe_allow_html=True)
        return
    cards = []
    for s in students:
        roles_txt = " &middot; ".join(s["roles"])
        cards.append(
            f'<details class="sm-card">'
            f'<summary class="sm-card-head">'
            f'<span class="sm-name">{s["name"]}</span>'
            f'<span class="sm-major">{s["major"]}</span>'
            f'<span class="sm-lib-tag">{s["year"]}</span>'
            f'<span class="sm-lib-tag">{s["course"]}</span>'
            '</summary>'
            '<div class="sm-detail">'
            f'<div class="sm-meta"><a class="sm-mail" href="mailto:{s["email"]}">{s["email"]}</a>'
            f' &middot; {s["major"]} &middot; {s["year"]}</div>'
            f'<div class="sm-roles">Roles: {roles_txt}</div>'
            '<div class="sm-detail-grid">'
            f'<div class="sm-radar">{radar_svg(s["stats"])}</div>'
            '<div class="sm-detail-right">'
            f'{stat_bars(s)}'
            f'<div class="sm-meta">Hours: {s["hours"]}/week &middot; Meets: {", ".join(s["meeting"])} &middot; Load: {", ".join(s["load"])}</div>'
            '</div></div></div></details>'
        )
    st.markdown("".join(cards), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Smart Match", page_icon="\U0001F91D")

st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --bg: #0a0a0c; --surface: #101013; --surface-2: #15151a;
  --line: #232329; --line-2: #34343d;
  --ink: #f2f1ed; --muted: #9a9aa3; --faint: #5f5f68;
  --red: #d9776e; --blue: #7d9bc6; --yellow: #c9a45c;
}

html, body { overflow-x: hidden; }

.stApp {
  background-color: var(--bg);
  background-image:
    linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,0.026) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.026) 1px, transparent 1px);
  background-size: 128px 128px, 128px 128px, 32px 32px, 32px 32px;
}
[data-testid="stHeader"] { background: transparent; }

.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 1100px !important;
  padding: 2rem 2.5rem 3rem;
}

/* section headers: mono index + geometric title + ticked rule */
.sm-section { display: flex; align-items: center; gap: 14px; margin: 36px 0 18px; }
.sm-sec-num { font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; font-weight: 600; color: var(--red); letter-spacing: 0.05em; }
.sm-sec-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.02rem; font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--ink); }
.sm-sec-line { flex: 1; height: 1px; background: var(--line); position: relative; }
.sm-sec-line::after { content: ""; position: absolute; right: 0; top: -3px; width: 7px; height: 7px; border: 1px solid var(--red); transform: rotate(45deg); }

/* form */
[data-testid="stForm"] {
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 4px solid var(--blue);
  padding: 34px 42px;
}
[data-testid="stWidgetLabel"] p { font-size: 0.85rem; color: var(--muted); margin-bottom: 0.4rem; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.03em; }

[data-testid="stFormSubmitButton"] button {
  background: var(--red); color: #0a0a0c; font-family: 'IBM Plex Mono', monospace; font-weight: 600;
  letter-spacing: 0.12em; text-transform: uppercase; border: none; border-radius: 0; padding: 0.75em 2.6em;
  transition: background 0.15s ease;
}
[data-testid="stFormSubmitButton"] button:hover { background: #ff6b6b; color: #0a0a0c; }

/* plain button */
[data-testid="stButton"] button {
  background: transparent; border: 1px solid var(--line); color: var(--muted);
  border-radius: 0; letter-spacing: 0.08em; text-transform: uppercase;
  font-family: 'IBM Plex Mono', monospace; font-weight: 500; padding: 0.45em 1.3em;
  transition: border-color 0.15s ease, color 0.15s ease;
}
[data-testid="stButton"] button:hover { border-color: var(--red); color: var(--red); }
[data-testid="stButton"] button[kind="primary"] {
  background: var(--red) !important; color: #0a0a0c !important; border: none !important; font-weight: 600;
}
[data-testid="stButton"] button[kind="primary"]:hover { background: #ff6b6b !important; color: #0a0a0c !important; }

/* header */
.sm-header { margin-bottom: 10px; display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.sm-logo { font-family: 'Space Grotesk', sans-serif; font-size: 2.4rem; font-weight: 700; letter-spacing: 0.04em; line-height: 1; color: var(--ink); }
.sm-logo .accent { color: var(--red); }
.sm-sub { color: var(--muted); letter-spacing: 0.04em; font-size: 0.82rem; font-family: 'IBM Plex Mono', monospace; }
.sm-rule { height: 2px; background: linear-gradient(90deg, var(--red), var(--line)); margin: 16px 0 8px; }

/* library head */
.sm-lib-head { font-family: 'Space Grotesk', sans-serif; font-size: 1.6rem; font-weight: 700; letter-spacing: 0.02em; color: var(--ink); }
.sm-lib-head .accent { color: var(--red); }
.sm-lib-count { color: var(--muted); font-size: 0.78rem; margin: 2px 0 18px; font-family: 'IBM Plex Mono', monospace; }

/* intro hero: geometric registration target */
.sm-hero { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 26px 0 8px; }
.sm-target { position: relative; width: 230px; height: 230px; margin-bottom: 30px; }
.sm-target .t1, .sm-target .t2, .sm-target .t3 {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  border: 1px solid var(--line-2);
}
.sm-target .t1 { width: 100%; height: 100%; animation: smSpin 60s linear infinite; }
.sm-target .t2 { width: 62%; height: 62%; }
.sm-target .t3 { width: 26%; height: 26%; border-color: var(--red); }
.sm-target::before, .sm-target::after { content: ""; position: absolute; background: var(--line-2); }
.sm-target::before { left: 50%; top: -4%; width: 1px; height: 108%; }
.sm-target::after { top: 50%; left: -4%; height: 1px; width: 108%; }
@keyframes smSpin { to { transform: translate(-50%, -50%) rotate(360deg); } }
.sm-hero-title { font-family: 'Space Grotesk', sans-serif; font-size: 3.4rem; font-weight: 700; letter-spacing: -0.01em; line-height: 1; color: var(--ink); }
.sm-hero-title .accent { color: var(--red); }
.sm-tagline { color: var(--muted); letter-spacing: 0.03em; margin-top: 12px; font-size: 0.9rem; font-family: 'IBM Plex Mono', monospace; }
.sm-chips { display: flex; gap: 10px; justify-content: center; margin: 24px 0 6px; flex-wrap: wrap; }
.sm-chip { border: 1px solid var(--line); color: var(--muted); font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; letter-spacing: 0.1em; padding: 6px 14px; }
.sm-chip:nth-child(1) { border-color: rgba(217,119,110,0.5); color: var(--red); }
.sm-chip:nth-child(2) { border-color: rgba(125,155,198,0.5); color: var(--blue); }
.sm-chip:nth-child(3) { border-color: rgba(201,164,92,0.5); color: var(--yellow); }

/* MATCH FOUND overlay: corner-bracket frame */
.sm-overlay {
  position: fixed; inset: 0; z-index: 999; display: flex; align-items: center; justify-content: center;
  background: rgba(10,10,12,0.95); pointer-events: none;
  animation: smOverlayOut 1.8s ease-out forwards;
}
@keyframes smOverlayOut { 0%, 72% { opacity: 1; } 100% { opacity: 0; visibility: hidden; } }
.sm-frame { position: relative; padding: 48px 64px; }
.sm-frame .c { position: absolute; width: 24px; height: 24px; border: 0 solid var(--red); }
.sm-frame .c.tl { top: 0; left: 0; border-top-width: 3px; border-left-width: 3px; }
.sm-frame .c.tr { top: 0; right: 0; border-top-width: 3px; border-right-width: 3px; }
.sm-frame .c.bl { bottom: 0; left: 0; border-bottom-width: 3px; border-left-width: 3px; }
.sm-frame .c.br { bottom: 0; right: 0; border-bottom-width: 3px; border-right-width: 3px; }
.sm-overlay-text {
  font-family: 'Space Grotesk', sans-serif; font-size: 3rem; font-weight: 700; letter-spacing: 0.18em;
  color: var(--red); text-shadow: 0 0 24px rgba(217,119,110,0.4); animation: smPop 0.4s ease-out;
}
.sm-overlay-sub { font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.3em; text-transform: uppercase; color: var(--muted); font-size: 0.72rem; margin-top: 14px; }
@keyframes smPop { from { transform: scale(0.7); opacity: 0; } to { transform: scale(1); opacity: 1; } }

/* results */
.sm-results-head { font-family: 'IBM Plex Mono', monospace; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--blue); border-left: 4px solid var(--blue); padding-left: 12px; margin: 22px 0 14px; font-size: 0.8rem; }

.sm-card { background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--blue); padding: 18px 24px; margin-bottom: 14px; transition: border-color 0.15s ease; }
.sm-card:hover { border-color: var(--line-2); border-left-color: var(--red); }
details[open].sm-card { border-left-color: var(--red); }
.sm-card.picked { border-color: rgba(217,119,110,0.5); border-left-color: var(--red); }

.sm-card-head { display: flex; align-items: baseline; gap: 14px; cursor: pointer; list-style: none; }
summary::-webkit-details-marker { display: none; }
summary::after { content: "[+]"; color: var(--red); font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; margin-left: 2px; }
details[open] summary::after { content: "[−]"; }
.sm-rank { color: var(--red); font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 0.9rem; }
.sm-name { font-family: 'Space Grotesk', sans-serif; font-size: 1.4rem; font-weight: 600; letter-spacing: 0.02em; color: var(--ink); }
.sm-major { color: var(--muted); font-size: 0.76rem; letter-spacing: 0.03em; font-family: 'IBM Plex Mono', monospace; }
.sm-score { margin-left: auto; font-family: 'IBM Plex Mono', monospace; font-size: 1.25rem; font-weight: 600; color: var(--red); }
.sm-lib-tag { color: var(--muted); font-size: 0.7rem; border: 1px solid var(--line); padding: 2px 8px; letter-spacing: 0.03em; font-family: 'IBM Plex Mono', monospace; }
.sm-picked-badge { color: var(--red); font-size: 0.66rem; letter-spacing: 0.1em; border: 1px solid var(--red); padding: 2px 8px; font-family: 'IBM Plex Mono', monospace; }

.sm-detail { margin-top: 16px; }
.sm-meta { color: var(--muted); font-size: 0.78rem; margin-bottom: 16px; font-family: 'IBM Plex Mono', monospace; }
.sm-mail { color: var(--blue); text-decoration: none; }
.sm-mail:hover { text-decoration: underline; }
.sm-roles { color: var(--ink); font-size: 0.82rem; margin: 2px 0 14px; }
.sm-detail-grid { display: grid; grid-template-columns: 300px 1fr; gap: 26px; align-items: start; }
.sm-radar { display: flex; justify-content: center; }

.sm-bar { display: grid; grid-template-columns: 150px 1fr 46px; align-items: center; gap: 12px; margin: 8px 0; }
.sm-bar-label { font-size: 0.68rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); font-family: 'IBM Plex Mono', monospace; white-space: nowrap; }
.sm-bar-track { background: var(--surface-2); height: 6px; }
.sm-bar-fill { background: var(--red); height: 6px; display: block; }
.sm-bar-val { font-size: 0.78rem; color: var(--ink); text-align: right; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }

.sm-analysis { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line); }
.sm-analysis-title { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.18em; color: var(--blue); margin-bottom: 8px; text-transform: uppercase; }
.sm-analysis p { color: var(--muted); font-size: 0.84rem; line-height: 1.6; margin: 5px 0; }
.sm-analysis b { color: var(--ink); }
.sm-verdict { color: var(--yellow) !important; font-weight: 600; margin-top: 10px !important; font-family: 'IBM Plex Mono', monospace; }
.sm-ai-tag { color: var(--faint); font-size: 0.6rem; letter-spacing: 0.08em; border: 1px solid var(--line); padding: 1px 6px; vertical-align: middle; font-weight: 500; font-family: 'IBM Plex Mono', monospace; }

/* team coverage */
.sm-coverage { background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--yellow); padding: 20px 24px; margin: 8px 0 22px; }
.sm-coverage-title { font-family: 'Space Grotesk', sans-serif; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink); font-size: 0.95rem; margin-bottom: 14px; }
.sm-cover-score { color: var(--yellow); margin-left: 10px; font-family: 'IBM Plex Mono', monospace; }
.sm-gap { margin-top: 14px; padding: 10px 12px; border: 1px solid rgba(201,164,92,0.4); color: var(--muted); font-size: 0.82rem; font-family: 'IBM Plex Mono', monospace; }
.sm-gap.ok { border-color: var(--line); color: var(--faint); }
.sm-gap b { color: var(--ink); }

.sm-note { color: var(--muted); font-size: 0.82rem; padding: 14px 18px; border: 1px dashed var(--line); margin-bottom: 18px; font-family: 'IBM Plex Mono', monospace; }

/* MATCH START overlay */
.sm-launch { position: fixed; inset: 0; z-index: 999; overflow: hidden; pointer-events: none; background: rgba(10,10,12,0.95); animation: smLaunchFade 1.9s ease-out forwards; }
@keyframes smLaunchFade { 0%, 78% { opacity: 1; } 100% { opacity: 0; visibility: hidden; } }
.sm-launch-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.sm-launch-text { font-family: 'Space Grotesk', sans-serif; font-size: 3rem; font-weight: 700; letter-spacing: 0.16em; color: var(--blue); text-shadow: 0 0 24px rgba(125,155,198,0.4); animation: smPop 0.4s ease-out; }
.sm-launch-sub { font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.3em; text-transform: uppercase; color: var(--muted); font-size: 0.72rem; margin-top: 14px; }

/* responsive */
@media (max-width: 720px) {
  .block-container, [data-testid="stMainBlockContainer"] { padding: 1.2rem 1rem 2.5rem; }
  [data-testid="stForm"] { padding: 22px 16px; }
  .sm-logo { font-size: 1.9rem; }
  .sm-hero-title { font-size: 2.4rem; }
  .sm-target { width: 170px; height: 170px; }
  .sm-detail-grid { grid-template-columns: 1fr; gap: 18px; }
  .sm-radar { justify-content: flex-start; }
  .sm-bar { grid-template-columns: 1fr 44px; row-gap: 4px; }
  .sm-bar-label { grid-column: 1 / -1; }
  .sm-card { padding: 14px 16px; }
  .sm-card-head { flex-wrap: wrap; gap: 8px 12px; }
  .sm-overlay-text, .sm-launch-text { font-size: 2rem; letter-spacing: 0.12em; }
  .sm-frame { padding: 32px 36px; }
}

/* reduced motion */
@media (prefers-reduced-motion: reduce) {
  .sm-target .t1 { animation: none !important; }
  .sm-overlay, .sm-launch { animation: none !important; opacity: 0 !important; visibility: hidden !important; }
}
</style>

<div class="sm-header">
  <div class="sm-logo">SMART <span class="accent">MATCH</span></div>
  <div class="sm-sub">AI teammate recommendation for HKUST group projects</div>
</div>
<div class="sm-rule"></div>
''', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# View routing
# ---------------------------------------------------------------------------
if "view" not in st.session_state:
    st.session_state.view = "intro"

if st.session_state.view == "intro":
    # --- title screen ---
    st.markdown(intro_hero(), unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        if st.button("START MATCHING", type="primary", use_container_width=True, key="start"):
            st.session_state.view = "form"
            st.session_state.just_started = True
            st.rerun()

elif st.session_state.view == "results":
    # --- teammate view ---
    if "user" not in st.session_state:
        st.session_state.view = "form"
        st.rerun()

    if st.session_state.get("just_matched"):
        st.markdown(match_overlay(), unsafe_allow_html=True)
        st.session_state.just_matched = False

    if st.button("← Back to questionnaire", key="back"):
        st.session_state.view = "form"
        st.rerun()

    user = st.session_state.user
    team_size = st.session_state.team_size
    ranked = match(user)
    self_name = st.session_state.get("self_name")
    if self_name:
        ranked = [r for r in ranked if r[1]["name"] != self_name]
    need = team_size - 1

    entry_by_name = {cand["name"]: (t, cand, b) for t, cand, b in ranked}
    shortlist = ranked[: team_size + EXTRA_CANDIDATES]

    # Greedy team assembly: teammates that together best cover the 7 skill areas.
    greedy = greedy_team([cand for _, cand, _ in ranked], need)
    greedy_names = [c["name"] for c in greedy]
    have = {cand["name"] for _, cand, _ in shortlist}
    for g in greedy:
        if g["name"] not in have:
            shortlist.append(entry_by_name[g["name"]])

    name_to_cand = {cand["name"]: cand for _, cand, _ in shortlist}
    short_names = [cand["name"] for _, cand, _ in shortlist]
    default_team = greedy_names

    if st.session_state.get("added_as"):
        anon_name, anon_email = st.session_state.added_as
        st.info(f"You were added to the matching pool anonymously as **{anon_name}** ({anon_email}).")
    st.caption("Ranked by TOPSIS multi-criteria analysis · recommended team auto-selected by greedy skill-coverage.")
    picked = st.multiselect(
        f"Assemble your team — pick {need} teammate(s) to update coverage",
        short_names, default=default_team, key="picked",
    )
    picked_cands = [name_to_cand[n] for n in picked if n in name_to_cand]

    st.markdown(team_coverage_html(picked_cands), unsafe_allow_html=True)
    render_results(shortlist, user, team_size, set(picked))

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    if st.button("📚 Browse the Sample Library →", type="primary", key="to_library"):
        st.session_state.view = "library"
        st.rerun()

elif st.session_state.view == "library":
    # --- sample library view ---
    st.markdown('<div class="sm-lib-head">SAMPLE <span class="accent">LIBRARY</span></div>'
                '<div class="sm-lib-count">Browse and filter all candidate profiles.</div>',
                unsafe_allow_html=True)

    if st.button("← Back to recommendations", key="back_recs"):
        st.session_state.view = "results"
        st.rerun()

    pool = candidate_pool()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        course_f = st.selectbox("Course", ["All"] + sorted({s["course"] for s in pool}))
    with c2:
        major_f = st.selectbox("Major", ["All"] + sorted({s["major"] for s in pool}))
    with c3:
        year_f = st.selectbox("Year", ["All", "Year 1", "Year 2", "Year 3", "Year 4"])
    with c4:
        name_q = st.text_input("Name")

    c5, c6 = st.columns(2)
    with c5:
        role_f = st.multiselect("Has role(s)", ALL_ROLES)
    with c6:
        ability = st.selectbox("Ability dimension", ["Any"] + RADAR_AXES)

    min_score = 0
    if ability != "Any":
        min_score = st.slider(f"Minimum {ability}", 0, 100, 50)

    students = pool
    if name_q:
        students = [s for s in students if name_q.lower() in s["name"].lower()]
    if course_f != "All":
        students = [s for s in students if s["course"] == course_f]
    if major_f != "All":
        students = [s for s in students if s["major"] == major_f]
    if year_f != "All":
        students = [s for s in students if s["year"] == year_f]
    if role_f:
        students = [s for s in students if set(role_f) & set(s["roles"])]
    if ability != "Any":
        students = [s for s in students if s["stats"][ability] >= min_score]

    st.caption(f"{len(students)} / {len(pool)} profiles match")
    render_library_cards(students)

else:
    # --- questionnaire view ---
    if st.session_state.get("just_started"):
        st.markdown(launch_overlay(), unsafe_allow_html=True)
        st.session_state.just_started = False
    with st.form("questionnaire"):
        st.markdown(section("01", "About you"), unsafe_allow_html=True)
        year = st.selectbox("Year of study", ["Year 1", "Year 2", "Year 3", "Year 4"])
        major = st.selectbox("Major", _MAJORS)
        course = st.text_input("Which course are you looking for teammates for?", value="COMP1945")
        team_size = st.selectbox("How many people per team in this course?", TEAM_SIZES)

        st.markdown(section("02", "Roles and skills"), unsafe_allow_html=True)
        roles = st.multiselect("Which roles have you actually taken in past projects?", ALL_ROLES)

        st.markdown(section("03", "Availability"), unsafe_allow_html=True)
        hours = st.radio("Hours per week you can commit", HOURS, horizontal=True)
        meeting = st.multiselect("Preferred meeting times", MEETING)
        load = st.multiselect("What else occupies your time outside coursework?", LOAD)

        st.markdown(section("04", "Goals and expectations"), unsafe_allow_html=True)
        grade = st.radio("Your target grade", GRADES)
        expect = st.radio("What do you expect from teammates?", EXPECT)

        st.markdown(section("05", "Working style"), unsafe_allow_html=True)
        discussion = st.radio("In discussion, you actually tended to...", DISCUSSION)
        decision = st.radio("When a decision was needed, you preferred...", DECISION)
        deadline = st.radio("How did you handle your last project's deadline?", DEADLINE)

        st.markdown(section("06", "Reliability"), unsafe_allow_html=True)
        reliability = st.radio("When your own parts were due, you usually delivered...", RELIABILITY)

        st.markdown(section("07", "Other"), unsafe_allow_html=True)
        pref_major = st.radio("Prefer teammates from", ["Same major", "Different major (complementary)", "Doesn't matter"])
        suggestion = st.text_area("Any suggestions for the system? (optional)")

        st.markdown(section("08", "Priority weights"), unsafe_allow_html=True)
        st.caption("Set each dimension from 0–100 (0 = don't care, 100 = most important). They're normalized automatically — max one and zero the rest if you like.")
        w_skills = st.slider("Skills complementarity", 0, 100, DEFAULT_WEIGHTS["Skills"], key="w_skills")
        w_avail = st.slider("Availability alignment", 0, 100, DEFAULT_WEIGHTS["Availability"], key="w_avail")
        w_style = st.slider("Working-style compatibility", 0, 100, DEFAULT_WEIGHTS["Working style"], key="w_style")
        w_goals = st.slider("Goals alignment", 0, 100, DEFAULT_WEIGHTS["Goals"], key="w_goals")
        w_reliab = st.slider("Reliability", 0, 100, DEFAULT_WEIGHTS["Reliability"], key="w_reliab")

        st.caption("By submitting, you agree that your answers are stored anonymously (under a generated name) to improve matching.")
        submitted = st.form_submit_button("Find teammates")

    if submitted:
        if not roles or not meeting:
            st.warning("Please pick at least one role and one meeting time.")
        else:
            st.session_state.user = {
                "course": course, "roles": roles, "hours": hours, "meeting": meeting,
                "load": load, "grade": grade, "expect": expect,
                "discussion": discussion, "decision": decision, "deadline": deadline,
                "reliability": reliability,
                "year": year, "major": major,
                "weights": {
                    "Skills": w_skills, "Availability": w_avail, "Working style": w_style,
                    "Goals": w_goals, "Reliability": w_reliab,
                },
            }
            st.session_state.team_size = int(team_size)
            profile = make_anonymized_profile(st.session_state.user, major)
            st.session_state.self_name = profile["name"]
            st.session_state.added_as = (profile["name"], profile["email"])
            save_respondent(profile)
            candidate_pool.clear()
            st.session_state.just_matched = True
            st.session_state.pop("picked", None)
            st.session_state.view = "results"
            st.rerun()
