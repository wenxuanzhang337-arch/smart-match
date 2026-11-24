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

# --- i18n: English / Simplified Chinese / Traditional Chinese ---
LANG_OPTIONS = {"English": "en", "简体中文": "zh-CN", "繁體中文": "zh-TW"}

_T = {
    "nav_title": {"en": "Navigation", "zh-CN": "导航", "zh-TW": "導航"},
    "nav_home": {"en": "Home", "zh-CN": "首页", "zh-TW": "首頁"},
    "nav_questionnaire": {"en": "Questionnaire", "zh-CN": "问卷", "zh-TW": "問卷"},
    "nav_team": {"en": "Team Analysis", "zh-CN": "团队分析", "zh-TW": "團隊分析"},
    "nav_database": {"en": "Database", "zh-CN": "数据库", "zh-TW": "資料庫"},
    "nav_profiles": {"en": "Major Profiles", "zh-CN": "专业画像", "zh-TW": "專業畫像"},
    "nav_logic": {"en": "How It Works", "zh-CN": "计算逻辑", "zh-TW": "計算邏輯"},
    "nav_feedback": {"en": "Feedback", "zh-CN": "反馈", "zh-TW": "回饋"},
    "nav_report": {"en": "Report", "zh-CN": "举报", "zh-TW": "舉報"},
    "hero_title": {"en": "FIND YOUR TEAM", "zh-CN": "找到你的团队", "zh-TW": "找到你的團隊"},
    "hero_tagline": {"en": "One short questionnaire. Matches scored across seven dimensions.", "zh-CN": "一份简短问卷，七维评分为你匹配。", "zh-TW": "一份簡短問卷，七維評分為你配對。"},
    "chip_topsis": {"en": "TOPSIS RANKING", "zh-CN": "TOPSIS 排序", "zh-TW": "TOPSIS 排序"},
    "chip_greedy": {"en": "GREEDY TEAMING", "zh-CN": "贪心组队", "zh-TW": "貪心組隊"},
    "chip_ai": {"en": "AI ANALYSIS", "zh-CN": "AI 分析", "zh-TW": "AI 分析"},
    "header_sub": {"en": "AI teammate recommendation for HKUST group projects", "zh-CN": "为港科大课程项目提供 AI 组队推荐", "zh-TW": "為港科大課程項目提供 AI 組隊推薦"},
    "start_matching": {"en": "START MATCHING", "zh-CN": "开始匹配", "zh-TW": "開始配對"},
}


def _lang():
    return LANG_OPTIONS.get(st.session_state.get("lang", "English"), "en")


def t(key):
    entry = _T.get(key, {})
    return entry.get(_lang(), entry.get("en", key))

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

# Base 7-axis skill profile per HKUST major, derived from typical learning content.
# Rough priors (0-100); they blend with a student's own role history in the stats.
MAJOR_PROFILES = {
    "Aerospace Engineering (AE)": {"Code": 65, "Writing": 55, "Speaking": 45, "Planning": 70, "Data": 60, "Design": 60, "Leadership": 40},
    "Biochemistry and Cell Biology (BCB)": {"Code": 45, "Writing": 65, "Speaking": 45, "Planning": 55, "Data": 60, "Design": 40, "Leadership": 40},
    "Bioengineering (BIEN)": {"Code": 60, "Writing": 55, "Speaking": 45, "Planning": 60, "Data": 60, "Design": 45, "Leadership": 40},
    "Biotechnology (BIOT)": {"Code": 45, "Writing": 60, "Speaking": 45, "Planning": 55, "Data": 60, "Design": 40, "Leadership": 40},
    "Biotechnology and Business (BIBU)": {"Code": 45, "Writing": 60, "Speaking": 55, "Planning": 60, "Data": 60, "Design": 40, "Leadership": 55},
    "Chemical and Environmental Engineering (CEEV)": {"Code": 55, "Writing": 60, "Speaking": 40, "Planning": 60, "Data": 55, "Design": 40, "Leadership": 40},
    "Chemistry (CHEM)": {"Code": 40, "Writing": 60, "Speaking": 40, "Planning": 55, "Data": 55, "Design": 40, "Leadership": 40},
    "Civil and Environmental Engineering (CIVL)": {"Code": 50, "Writing": 60, "Speaking": 45, "Planning": 65, "Data": 50, "Design": 55, "Leadership": 45},
    "Computer Engineering (CPEG)": {"Code": 85, "Writing": 45, "Speaking": 40, "Planning": 55, "Data": 70, "Design": 40, "Leadership": 40},
    "Computer Science (COMP)": {"Code": 92, "Writing": 45, "Speaking": 40, "Planning": 50, "Data": 80, "Design": 40, "Leadership": 40},
    "Data Science and Technology (DSCT)": {"Code": 80, "Writing": 50, "Speaking": 45, "Planning": 55, "Data": 90, "Design": 45, "Leadership": 45},
    "Decision Analytics (DA)": {"Code": 60, "Writing": 55, "Speaking": 50, "Planning": 60, "Data": 80, "Design": 45, "Leadership": 50},
    "Economics (ECON)": {"Code": 45, "Writing": 65, "Speaking": 55, "Planning": 55, "Data": 70, "Design": 40, "Leadership": 45},
    "Economics and Finance (ECOF)": {"Code": 45, "Writing": 60, "Speaking": 55, "Planning": 55, "Data": 75, "Design": 40, "Leadership": 45},
    "Electronic Engineering (ELEC)": {"Code": 80, "Writing": 45, "Speaking": 40, "Planning": 55, "Data": 60, "Design": 40, "Leadership": 40},
    "Environmental Management and Technology (EVMT)": {"Code": 45, "Writing": 65, "Speaking": 55, "Planning": 65, "Data": 55, "Design": 45, "Leadership": 55},
    "Finance (FINA)": {"Code": 45, "Writing": 55, "Speaking": 55, "Planning": 55, "Data": 75, "Design": 40, "Leadership": 50},
    "General Business Management (GBM)": {"Code": 30, "Writing": 46, "Speaking": 46, "Planning": 46, "Data": 40, "Design": 40, "Leadership": 46},
    "Global Business (GBUS)": {"Code": 35, "Writing": 60, "Speaking": 70, "Planning": 60, "Data": 55, "Design": 45, "Leadership": 70},
    "Global China Studies (GCST)": {"Code": 30, "Writing": 75, "Speaking": 65, "Planning": 50, "Data": 45, "Design": 40, "Leadership": 50},
    "Individualized Interdisciplinary Major (IIM)": {"Code": 50, "Writing": 55, "Speaking": 55, "Planning": 55, "Data": 55, "Design": 55, "Leadership": 55},
    "Industrial Engineering and Engineering Management (IEEM)": {"Code": 50, "Writing": 60, "Speaking": 55, "Planning": 75, "Data": 65, "Design": 45, "Leadership": 60},
    "Information Systems (IS)": {"Code": 75, "Writing": 52, "Speaking": 52, "Planning": 55, "Data": 55, "Design": 45, "Leadership": 52},
    "Integrative Systems and Design (ISD)": {"Code": 55, "Writing": 50, "Speaking": 55, "Planning": 60, "Data": 50, "Design": 85, "Leadership": 55},
    "Management (MGMT)": {"Code": 35, "Writing": 60, "Speaking": 65, "Planning": 65, "Data": 50, "Design": 45, "Leadership": 75},
    "Marketing (MARK)": {"Code": 35, "Writing": 65, "Speaking": 70, "Planning": 60, "Data": 55, "Design": 70, "Leadership": 55},
    "Mathematics (MATH)": {"Code": 70, "Writing": 55, "Speaking": 40, "Planning": 55, "Data": 70, "Design": 40, "Leadership": 40},
    "Mathematics and Economics (MAEC)": {"Code": 60, "Writing": 55, "Speaking": 45, "Planning": 55, "Data": 75, "Design": 40, "Leadership": 45},
    "Mechanical Engineering (MECH)": {"Code": 60, "Writing": 50, "Speaking": 45, "Planning": 60, "Data": 55, "Design": 65, "Leadership": 45},
    "Ocean Science and Technology (OCES)": {"Code": 50, "Writing": 55, "Speaking": 45, "Planning": 55, "Data": 60, "Design": 40, "Leadership": 45},
    "Operations Management (OM)": {"Code": 50, "Writing": 55, "Speaking": 55, "Planning": 75, "Data": 65, "Design": 45, "Leadership": 60},
    "Physics (PHYS)": {"Code": 65, "Writing": 55, "Speaking": 40, "Planning": 55, "Data": 65, "Design": 40, "Leadership": 40},
    "Professional Accounting (PACC)": {"Code": 45, "Writing": 60, "Speaking": 50, "Planning": 65, "Data": 60, "Design": 40, "Leadership": 45},
    "Quantitative Finance (QFIN)": {"Code": 60, "Writing": 55, "Speaking": 50, "Planning": 55, "Data": 80, "Design": 40, "Leadership": 45},
    "Quantitative Social Analysis (QSA)": {"Code": 55, "Writing": 65, "Speaking": 55, "Planning": 55, "Data": 75, "Design": 40, "Leadership": 45},
    "Risk Management and Business Intelligence (RMBI)": {"Code": 70, "Writing": 55, "Speaking": 55, "Planning": 60, "Data": 80, "Design": 40, "Leadership": 50},
    "Sustainable and Green Finance (SGFN)": {"Code": 40, "Writing": 60, "Speaking": 55, "Planning": 60, "Data": 65, "Design": 40, "Leadership": 50},
    "Sustainable Energy Engineering (SUSEE)": {"Code": 55, "Writing": 55, "Speaking": 45, "Planning": 60, "Data": 55, "Design": 45, "Leadership": 45},
}


# Overall admission difficulty + reputation offset per major (additive, applied to all 7 axes).
# Grounded in JUPAS entry scores / program competitiveness: quantitative-finance and business
# programs sit highest, engineering/sciences mid, humanities and niche science lower.
MAJOR_TIER = {
    "Quantitative Finance (QFIN)": 15,
    "Global Business (GBUS)": 12,
    "Economics and Finance (ECOF)": 11,
    "Risk Management and Business Intelligence (RMBI)": 8,
    "Computer Science (COMP)": 7,
    "Data Science and Technology (DSCT)": 7,
    "Information Systems (IS)": 3,
    "Computer Engineering (CPEG)": 6,
    "Finance (FINA)": 6,
    "Economics (ECON)": 5,
    "Mathematics and Economics (MAEC)": 5,
    "Decision Analytics (DA)": 5,
    "Mathematics (MATH)": 5,
    "Electronic Engineering (ELEC)": 4,
    "Aerospace Engineering (AE)": 4,
    "Physics (PHYS)": 4,
    "Sustainable and Green Finance (SGFN)": 4,
    "Operations Management (OM)": 3,
    "Mechanical Engineering (MECH)": 2,
    "Bioengineering (BIEN)": 2,
    "Integrative Systems and Design (ISD)": 2,
    "Industrial Engineering and Engineering Management (IEEM)": 2,
    "Marketing (MARK)": 2,
    "Management (MGMT)": 2,
    "Professional Accounting (PACC)": 2,
    "Biotechnology and Business (BIBU)": 2,
    "Civil and Environmental Engineering (CIVL)": 1,
    "Chemical and Environmental Engineering (CEEV)": 1,
    "Chemistry (CHEM)": 1,
    "Biochemistry and Cell Biology (BCB)": 1,
    "Biotechnology (BIOT)": 1,
    "Environmental Management and Technology (EVMT)": 1,
    "Sustainable Energy Engineering (SUSEE)": 1,
    "General Business Management (GBM)": -4,
    "Quantitative Social Analysis (QSA)": 1,
    "Individualized Interdisciplinary Major (IIM)": 0,
    "Ocean Science and Technology (OCES)": -4,
    "Global China Studies (GCST)": -4,
}

# Entry-barrier adjustment: demanding processes (interview / written test, GPA 3.3+ declaration)
# lift a major; easy "one-course" declaration discounts it (mixed intake). Not surfaced in rationale.
MAJOR_BARRIER = {
    "Quantitative Finance (QFIN)": 5, "Global Business (GBUS)": 5,
    "Economics and Finance (ECOF)": 4, "Risk Management and Business Intelligence (RMBI)": 5,
    "Computer Science (COMP)": 3, "Data Science and Technology (DSCT)": 3,
    "Mathematics and Economics (MAEC)": 3,
    "Computer Engineering (CPEG)": 2, "Electronic Engineering (ELEC)": 2,
    "Decision Analytics (DA)": 2, "Finance (FINA)": 2, "Professional Accounting (PACC)": 2,
    "Economics (ECON)": 1, "Mathematics (MATH)": 1, "Physics (PHYS)": 1,
    "Quantitative Social Analysis (QSA)": 1, "Sustainable and Green Finance (SGFN)": 1,
    "Aerospace Engineering (AE)": 0, "Bioengineering (BIEN)": 0,
    "Chemical and Environmental Engineering (CEEV)": 0, "Civil and Environmental Engineering (CIVL)": 0,
    "Mechanical Engineering (MECH)": 0, "Industrial Engineering and Engineering Management (IEEM)": 0,
    "Sustainable Energy Engineering (SUSEE)": 0, "Integrative Systems and Design (ISD)": 0,
    "Biotechnology and Business (BIBU)": 0, "Individualized Interdisciplinary Major (IIM)": 0,
    "Environmental Management and Technology (EVMT)": -1,
    "Marketing (MARK)": -2, "Management (MGMT)": -2, "Operations Management (OM)": -2,
    "General Business Management (GBM)": -3, "Biochemistry and Cell Biology (BCB)": -2,
    "Biotechnology (BIOT)": -2, "Chemistry (CHEM)": -2,
    "Information Systems (IS)": -3, "Global China Studies (GCST)": -3,
    "Ocean Science and Technology (OCES)": -3,
}


def _clamp_stat(v):
    return max(30, min(95, v))


def major_profile(major):
    """Content shape shifted by overall tier + entry barrier, then widened 1.5x."""
    base = MAJOR_PROFILES.get(major, {a: 50 for a in RADAR_AXES})
    off = round((MAJOR_TIER.get(major, 0) + MAJOR_BARRIER.get(major, 0)) * 1.5)
    return {a: _clamp_stat(v + off) for a, v in base.items()}


def _major_stats(major, rng=None):
    """Final 7-axis profile for a major, optionally with small per-person jitter."""
    base = major_profile(major)
    if rng is None:
        return dict(base)
    return {a: _clamp_stat(v + rng.randint(-8, 8)) for a, v in base.items()}


# Why each major's 7-axis profile is distributed the way it is.
MAJOR_RATIONALE = {
    "Aerospace Engineering (AE)": "Aerodynamics, structures and flight mechanics favour maths, simulation and careful planning; less writing and speaking.",
    "Biochemistry and Cell Biology (BCB)": "Lab-centred with heavy scientific writing and data interpretation; little coding or design.",
    "Bioengineering (BIEN)": "Bridges engineering and life science — coding and data plus lab write-ups; lighter on speaking.",
    "Biotechnology (BIOT)": "Research-oriented with report writing and data analysis; little programming or design.",
    "Biotechnology and Business (BIBU)": "Pairs science with business, so writing, speaking and leadership stay balanced.",
    "Chemical and Environmental Engineering (CEEV)": "Process and environmental design demand technical writing and planning; limited speaking.",
    "Chemistry (CHEM)": "Lab-heavy with extensive report writing and data handling; minimal coding or design.",
    "Civil and Environmental Engineering (CIVL)": "Structural design and site analysis need planning, writing and some design; modest speaking.",
    "Computer Engineering (CPEG)": "Hardware plus software — strong coding and data; less writing and speaking.",
    "Computer Science (COMP)": "Programming- and algorithm-heavy, so Code and Data dominate; little presentation or writing practice.",
    "Data Science and Technology (DSCT)": "Math, statistics and machine learning make Data and Code the peaks; speaking and design stay low.",
    "Decision Analytics (DA)": "Optimization and data-driven decisions — strong Data and Planning with balanced communication.",
    "Economics (ECON)": "Theory, econometrics and essays — strong writing and data; little coding or design.",
    "Economics and Finance (ECOF)": "Quantitative finance and essays — high data and writing; little design.",
    "Electronic Engineering (ELEC)": "Circuits and systems favour coding and maths; less writing and speaking.",
    "Environmental Management and Technology (EVMT)": "Policy plus environmental science — writing, planning and communication; less coding.",
    "Finance (FINA)": "Valuation, markets and modelling — strong data plus presentation; little coding or design.",
    "General Business Management (GBM)": "Broad management develops leadership, speaking and planning; minimal technical work.",
    "Global Business (GBUS)": "International business and negotiation — top speaking and leadership; minimal coding.",
    "Global China Studies (GCST)": "Humanities and social analysis — strongest writing and speaking; little maths or coding.",
    "Individualized Interdisciplinary Major (IIM)": "Student-designed, so it defaults to a balanced profile across all axes.",
    "Industrial Engineering and Engineering Management (IEEM)": "Process optimisation and operations — planning, data and leadership; moderate writing.",
    "Information Systems (IS)": "Strong on coding and IT, but otherwise a fairly general business profile.",
    "Integrative Systems and Design (ISD)": "Design thinking and prototyping — top design plus planning; lighter on coding.",
    "Management (MGMT)": "People and organisations — leadership, speaking and planning; little technical work.",
    "Marketing (MARK)": "Consumer insight and creative campaigns — speaking, design and writing; little coding.",
    "Mathematics (MATH)": "Pure and applied maths — strong code and data; less writing and speaking.",
    "Mathematics and Economics (MAEC)": "Quantitative economics — strong data and code; modest writing and speaking.",
    "Mechanical Engineering (MECH)": "Mechanics, CAD and prototyping — design and planning plus decent coding and data.",
    "Ocean Science and Technology (OCES)": "Field and lab science — data and writing; less speaking or design.",
    "Operations Management (OM)": "Supply chains and processes — planning, data and leadership; less coding.",
    "Physics (PHYS)": "Theory and experiment — strong code and data; less speaking or design.",
    "Professional Accounting (PACC)": "Financial reporting and audit — planning, writing and data; little coding.",
    "Quantitative Finance (QFIN)": "Math and finance modelling — top data plus coding; moderate speaking.",
    "Quantitative Social Analysis (QSA)": "Social statistics — strong data and writing; moderate speaking; little design.",
    "Risk Management and Business Intelligence (RMBI)": "Risk models and business intelligence — strong data, coding and planning; moderate leadership.",
    "Sustainable and Green Finance (SGFN)": "Finance plus sustainability — data, writing and planning; little coding.",
    "Sustainable Energy Engineering (SUSEE)": "Energy systems and policy — planning, writing and analysis; moderate coding.",
}


# Name pools for the 50 simulated respondents: 1/3 Mainland pinyin, 1/3 Cantonese, 1/3 foreign.
_MAINLAND_SURNAMES = ["Zhang", "Wang", "Li", "Liu", "Chen", "Yang", "Huang", "Zhao", "Wu", "Zhou", "Xu", "Sun", "Ma", "Zhu", "Hu", "Guo", "He", "Gao", "Lin", "Luo"]
_MAINLAND_GIVEN = ["Wei", "Fang", "Ming", "Yang", "Jie", "Lei", "Min", "Jun", "Hao", "Xin", "Yuxuan", "Haoran", "Zixuan", "Yifan", "Shanshan", "Xiaotong", "Yuchen", "Jingyi", "Ruoxi", "Minghao"]
_CANTO_SURNAMES = ["Chan", "Wong", "Lee", "Ng", "Ho", "Lam", "Cheung", "Lau", "Tam", "Yip", "Leung", "Chow", "Fung", "Kwok", "Tang", "Tsang", "Mak", "Poon", "Siu", "To"]
_CANTO_GIVEN = ["Tai Man", "Ka Yan", "Wai Ming", "Siu Ling", "Chun Kit", "Wing Shan", "Chi Ho", "Mei Ling", "Wing Cheung", "Ka Wai", "Sze Hang", "Hiu Tung", "Ching Yee", "Ho Yin", "Man Ho", "Yan Ting", "Ka Ho", "Wing Lam", "Chun Yin", "Tsz Ching"]
_FOREIGN_FIRST = ["John", "Mary", "David", "Sarah", "Michael", "Emily", "James", "Emma", "Daniel", "Olivia", "Lucas", "Sophia", "Ethan", "Isabella", "Alexander", "Ava", "William", "Mia", "Ryan", "Chloe"]
_FOREIGN_LAST = ["Smith", "Johnson", "Garcia", "Brown", "Williams", "Jones", "Miller", "Davis", "Rodriguez", "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Perez", "Thompson", "White", "Harris"]


def _random_name(rng, idx):
    cat = idx % 3
    if cat == 0:
        return f"{rng.choice(_MAINLAND_SURNAMES)} {rng.choice(_MAINLAND_GIVEN)}"
    if cat == 1:
        return f"{rng.choice(_CANTO_SURNAMES)} {rng.choice(_CANTO_GIVEN)}"
    return f"{rng.choice(_FOREIGN_FIRST)} {rng.choice(_FOREIGN_LAST)}"


def build_sample_library(n=50, seed=7):
    """50 simulated respondents who 'fill the questionnaire' — every answer is
    random except the course (COMP1945); stats are derived from major + roles
    via the same formula used for real respondents."""
    rng = random.Random(seed)
    students = []
    seen_names = set()
    seen_emails = set()
    for i in range(n):
        name = email = None
        for _ in range(200):
            cname = _random_name(rng, i)
            cemail = cname.lower().replace(" ", ".") + "@connect.ust.hk"
            if cname not in seen_names and cemail not in seen_emails:
                name, email = cname, cemail
                break
        if name is None:
            name, email = f"Student {i + 1}", f"student{i + 1}@connect.ust.hk"
        seen_names.add(name)
        seen_emails.add(email)

        roles = rng.sample(ALL_ROLES, rng.choice([1, 2, 2, 3]))
        major = rng.choice(_MAJORS)
        weights = {k: rng.randint(0, 100) for k in ["Skills", "Availability", "Working style", "Goals", "Reliability"]}
        stats = _major_stats(major, rng)
        for r in roles:
            for axis, bonus in _ROLE_STAT_BONUS[r].items():
                stats[axis] = min(95, stats[axis] + bonus)

        busy = ["Internship", "Part-time job", "Job-hunting", "Graduate-school applications"]
        load = ["None of the above"] if rng.random() < 0.4 else rng.sample(busy, rng.randint(1, 2))

        students.append({
            "name": name, "email": email, "major": major,
            "gender": rng.choice(["Male", "Female"]),
            "year": rng.choice(["Year 1", "Year 2", "Year 3", "Year 4"]),
            "course": "COMP1945", "roles": roles,
            "hours": rng.choice(HOURS),
            "meeting": rng.sample(MEETING, rng.randint(1, 3)),
            "load": load,
            "grade": rng.choice(GRADES), "expect": rng.choice(EXPECT),
            "discussion": rng.choice(DISCUSSION), "decision": rng.choice(DECISION),
            "deadline": rng.choice(DEADLINE), "reliability": rng.choice(RELIABILITY),
            "weights": weights,
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
            "major": row.get("major"), "year": row.get("year"), "gender": row.get("gender"),
            "course": row.get("course"), "roles": row.get("roles") or [],
            "hours": row.get("hours"), "meeting": row.get("meeting") or [],
            "load": row.get("load") or [], "grade": row.get("grade"),
            "expect": row.get("expect"), "discussion": row.get("discussion"),
            "decision": row.get("decision"), "deadline": row.get("deadline"),
            "reliability": row.get("reliability"), "weights": row.get("weights") or {}, "stats": row.get("stats") or {},
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


def _comments_url():
    base = st.secrets.get("SUPABASE_URL", "").strip().rstrip("/")
    return f"{base}/rest/v1/comments" if base else ""


def fetch_comments():
    """Return a list of {author, body, created_at}, newest first."""
    url = _comments_url()
    if not url:
        return []
    try:
        r = requests.get(f"{url}?select=*&order=created_at.desc", headers=_supabase_headers(), timeout=15)
        if r.status_code != 200:
            return []
        return [{
            "author": row.get("author") or "Anonymous",
            "body": row.get("body") or "",
            "created_at": row.get("created_at") or "",
        } for row in r.json()]
    except Exception:
        return []


def save_comment(author, body):
    """Insert one comment into Supabase. Returns True on success."""
    url = _comments_url()
    if not url or not st.secrets.get("SUPABASE_ANON_KEY", ""):
        return False
    try:
        r = requests.post(url, headers={**_supabase_headers(), "Prefer": "return=minimal"},
                          json={"author": author, "body": body}, timeout=15)
        return r.status_code in (200, 201, 204)
    except Exception:
        return False


REPORT_LABELS = [
    "Freerider / doesn't contribute",
    "Refuses to listen to suggestions",
    "Lone wolf / doesn't communicate",
    "Repeated conflicts with teammates",
]


def _reports_url():
    base = st.secrets.get("SUPABASE_URL", "").strip().rstrip("/")
    return f"{base}/rest/v1/reports" if base else ""


def _praise_url():
    base = st.secrets.get("SUPABASE_URL", "").strip().rstrip("/")
    return f"{base}/rest/v1/praise" if base else ""


def fetch_reports():
    url = _reports_url()
    if not url:
        return []
    try:
        r = requests.get(f"{url}?select=*", headers=_supabase_headers(), timeout=15)
        if r.status_code != 200:
            return []
        return [{"target_name": row.get("target_name"), "label": row.get("label"),
                 "verdict": row.get("verdict")} for row in r.json()]
    except Exception:
        return []


def fetch_praise():
    url = _praise_url()
    if not url:
        return []
    try:
        r = requests.get(f"{url}?select=*", headers=_supabase_headers(), timeout=15)
        if r.status_code != 200:
            return []
        return [row.get("target_name") for row in r.json()]
    except Exception:
        return []


def save_report(target_name, label, evidence, verdict):
    url = _reports_url()
    if not url or not st.secrets.get("SUPABASE_ANON_KEY", ""):
        return False
    try:
        r = requests.post(url, headers={**_supabase_headers(), "Prefer": "return=minimal"},
                          json={"target_name": target_name, "label": label,
                                "evidence": evidence, "verdict": verdict}, timeout=15)
        return r.status_code in (200, 201, 204)
    except Exception:
        return False


def save_praise(target_name):
    url = _praise_url()
    if not url or not st.secrets.get("SUPABASE_ANON_KEY", ""):
        return False
    try:
        r = requests.post(url, headers={**_supabase_headers(), "Prefer": "return=minimal"},
                          json={"target_name": target_name}, timeout=15)
        return r.status_code in (200, 201, 204)
    except Exception:
        return False


@st.cache_data(ttl=300, show_spinner=False)
def flagged_people():
    """{name: [labels]} for people with >=2 approved reports and <2 praise."""
    from collections import Counter
    rep_by_name = {}
    for r in fetch_reports():
        if r.get("verdict") != "approved":
            continue
        rep_by_name.setdefault(r["target_name"], []).append(r["label"])
    praise_count = Counter(fetch_praise())
    out = {}
    for name, labels in rep_by_name.items():
        if len(labels) >= 2 and praise_count.get(name, 0) < 2:
            out[name] = list(dict.fromkeys(labels))
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def llm_report_review(target_name, label, evidence):
    """Ask DeepSeek to approve/reject a report based on the evidence."""
    try:
        key = st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        return "approved"
    if not key:
        return "approved"
    prompt = (
        "You moderate reports in a student team-matching app.\n"
        f"Reported teammate: {target_name}\nLabel (misconduct): {label}\n\n"
        f"Evidence:\n{evidence[:3000]}\n\n"
        "Does the evidence plausibly support the label? Answer exactly one word: APPROVE or REJECT."
    )
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": st.secrets.get("DEEPSEEK_MODEL", "deepseek-chat"),
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.0, "max_tokens": 8},
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip().upper()
        return "rejected" if "REJECT" in text else "approved"
    except Exception:
        return "approved"


def flag_badges(name, flagged):
    labels = flagged.get(name, [])
    return "".join(f'<span class="sm-flag-tag">{l}</span>' for l in labels)


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
    stats = _major_stats(major, rng)
    for r in user["roles"]:
        for axis, bonus in _ROLE_STAT_BONUS.get(r, {}).items():
            stats[axis] = min(95, stats[axis] + bonus)
    return {
        "name": name, "email": email, "major": major, "gender": user.get("gender"), "year": user.get("year"),
        "course": user["course"], "roles": list(user["roles"]),
        "hours": user["hours"], "meeting": list(user["meeting"]), "load": list(user["load"]),
        "grade": user["grade"], "expect": user["expect"],
        "discussion": user["discussion"], "decision": user["decision"],
        "deadline": user["deadline"], "reliability": user["reliability"], "weights": user.get("weights") or {},
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
        f'<div class="sm-hero-title">{t("hero_title")}</div>'
        f'<div class="sm-tagline">{t("hero_tagline")}</div>'
        '<div class="sm-chips">'
        f'<span class="sm-chip">{t("chip_topsis")}</span>'
        f'<span class="sm-chip">{t("chip_greedy")}</span>'
        f'<span class="sm-chip">{t("chip_ai")}</span>'
        '</div>'
        '</div>'
    )


def boot_overlay():
    """Geometric 'assembly' transition played once on entry."""
    return (
        '<div class="sm-boot">'
        '<div class="sm-boot-grid"></div>'
        '<div class="sm-boot-cross-h"></div><div class="sm-boot-cross-v"></div>'
        '<div class="sm-boot-square s1"></div>'
        '<div class="sm-boot-square s2"></div>'
        '<div class="sm-boot-square s3"></div>'
        '<div class="sm-boot-diamond"></div>'
        '<div class="sm-boot-word">SMART <span>MATCH</span></div>'
        '<div class="sm-boot-coord">22.3373&deg;N &middot; 114.2630&deg;E</div>'
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


def _skill_axes(person):
    """Strong skill axes implied by a person's roles plus their major's learning content."""
    axes = set()
    for r in person.get("roles", []):
        axes |= set(_ROLE_STAT_BONUS.get(r, {}).keys())
    prof = major_profile(person.get("major", ""))
    axes |= {a for a, v in prof.items() if v >= 60}
    return axes


def score_roles(user, cand):
    """Complementarity: do they cover roles/skills I lack, without merely duplicating what I already do?"""
    my = set(user["roles"])
    their = set(cand["roles"])
    if their:
        brings = their - my
        overlap = their & my
        role_score = max(0.0, len(brings) / len(their) - 0.5 * len(overlap) / len(their))
    else:
        role_score = 0.0
    u_axes = _skill_axes(user)
    c_axes = _skill_axes(cand)
    if c_axes:
        s_brings = c_axes - u_axes
        s_overlap = c_axes & u_axes
        skill_score = max(0.0, len(s_brings) / len(c_axes) - 0.5 * len(s_overlap) / len(c_axes))
    else:
        skill_score = 0.0
    return 0.6 * role_score + 0.4 * skill_score


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


def _gender_valid(genders):
    from collections import Counter
    c = Counter(g for g in genders if g in ("Male", "Female"))
    return all(v != 1 for v in c.values())


def fix_team_gender(team, ranked_pool, user_gender):
    """Swap teammates so no gender ends up as the lone member (count == 1)."""
    team = list(team)
    if user_gender not in ("Male", "Female"):
        return team
    picked_names = {c["name"] for c in team}
    for _ in range(len(team) + 3):
        genders = [user_gender] + [c.get("gender") for c in team]
        if _gender_valid(genders):
            break
        from collections import Counter
        c = Counter(g for g in genders if g in ("Male", "Female"))
        lone = next((g for g in ("Male", "Female") if c.get(g, 0) == 1), None)
        if lone is None:
            break
        other = "Female" if lone == "Male" else "Male"
        idx = next((i for i, x in enumerate(team) if x.get("gender") == lone), None)
        target = other
        if idx is None:
            idx = next((i for i, x in enumerate(team) if x.get("gender") == other), None)
            target = lone
        if idx is None:
            break
        repl = next((x for x in ranked_pool if x["name"] not in picked_names and x.get("gender") == target), None)
        if repl is None:
            break
        team[idx] = repl
        picked_names = {c["name"] for c in team}
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


def major_profiles_html():
    """Clickable accordion: major name -> radar + rationale with a geometric reveal."""
    items = []
    for i, major in enumerate(MAJOR_PROFILES.keys(), 1):
        prof = major_profile(major)
        why = MAJOR_RATIONALE.get(major, "")
        off = MAJOR_TIER.get(major, 0)
        tier = ("Elite" if off >= 10 else "High" if off >= 6 else "Solid" if off >= 1
                else "Average" if off >= 0 else "Below avg")
        ranked = sorted(prof.items(), key=lambda kv: kv[1], reverse=True)
        strong = ranked[:2]
        weak = sorted(prof.items(), key=lambda kv: kv[1])[:2]
        strong_html = "".join(f'<span class="sm-mtag hi">{a} {v}</span>' for a, v in strong)
        weak_html = "".join(f'<span class="sm-mtag lo">{a} {v}</span>' for a, v in weak)
        items.append(
            '<details class="sm-major">'
            f'<summary class="sm-major-head"><span class="sm-major-idx">{i:02d}</span>'
            f'<span class="sm-major-name">{major}</span>'
            f'<span class="sm-major-hint">{strong[0][0]} · {strong[1][0]}</span></summary>'
            '<div class="sm-major-body"><div class="sm-detail-grid">'
            f'<div class="sm-radar">{radar_svg(prof)}</div>'
            '<div class="sm-major-info">'
            f'<p class="sm-major-why">{why}</p>'
            f'<div class="sm-major-tags"><span class="sm-mtag-lbl">Level</span><span class="sm-mtag tier">{tier}</span></div>'
            f'<div class="sm-major-tags"><span class="sm-mtag-lbl">Strong</span>{strong_html}</div>'
            f'<div class="sm-major-tags"><span class="sm-mtag-lbl">Weaker</span>{weak_html}</div>'
            '</div></div></div></details>'
        )
    return '<div class="sm-major-list">' + "".join(items) + '</div>'


def ping_overlay(label):
    """Brief full-screen geometric 'ping' feedback (crosshair + concentric squares)."""
    return (
        '<div class="sm-ping">'
        '<div class="sm-ping-cross-h"></div><div class="sm-ping-cross-v"></div>'
        '<div class="sm-ping-square s1"></div><div class="sm-ping-square s2"></div>'
        f'<div class="sm-ping-text">{label}</div>'
        '</div>'
    )


def _team_analysis_prompt(team):
    lines = []
    for c in team:
        lines.append(
            f"- {c['name']} ({c['major']}, {c.get('gender') or 'unknown'}): "
            f"roles: {', '.join(c['roles']) if c.get('roles') else 'none'}; "
            f"abilities Code={c['stats']['Code']}, Writing={c['stats']['Writing']}, Speaking={c['stats']['Speaking']}, "
            f"Planning={c['stats']['Planning']}, Data={c['stats']['Data']}, Design={c['stats']['Design']}, Leadership={c['stats']['Leadership']}."
        )
    max_stats = {a: max(c["stats"][a] for c in team) for a in RADAR_AXES}
    gaps = [a for a in RADAR_AXES if max_stats[a] < 60]
    return (
        PROJECT_CONTEXT + "\n\n"
        "YOUR TASK: Analyze this formed team. Write plain text (no markdown headings), about 300-500 words, covering: "
        "1) overall assessment, 2) STRENGTHS (short '-' bullets), 3) WEAKNESSES / coverage gaps ('-' bullets), "
        "4) concrete suggestions to amplify strengths and fix the gaps ('-' bullets).\n\n"
        "TEAM:\n" + "\n".join(lines) +
        f"\n\nCombined team max per axis: {max_stats}.\n"
        f"Coverage gaps (no member strong in): {', '.join(gaps) or 'none'}."
    )


def team_analysis_html(text):
    if not text:
        return ('<div class="sm-analysis"><div class="sm-analysis-title">Team Analysis</div>'
                '<p>Could not reach the AI service — try again later.</p></div>')
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    return ('<div class="sm-analysis sm-team-analysis">'
            '<div class="sm-analysis-title">Team Analysis <span class="sm-ai-tag">DeepSeek</span></div>'
            f'<p>{safe}</p></div>')


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
    flagged = flagged_people()
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
            f'<span class="sm-name">{cand["name"]}</span>{flag_badges(cand["name"], flagged)}'
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
    flagged = flagged_people()
    for s in students:
        roles_txt = " &middot; ".join(s["roles"])
        cards.append(
            f'<details class="sm-card">'
            f'<summary class="sm-card-head">'
            f'<span class="sm-name">{s["name"]}</span>{flag_badges(s["name"], flagged)}'
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

/* ---- geometric boot / entry transition ---- */
@keyframes bootGrid { 0% { opacity: 0; } 15% { opacity: 1; } 60% { opacity: 0.35; } 100% { opacity: 0; } }
@keyframes bootCrossH { from { transform: scaleX(0); opacity: 0; } to { transform: scaleX(1); opacity: 1; } }
@keyframes bootCrossV { from { transform: scaleY(0); opacity: 0; } to { transform: scaleY(1); opacity: 1; } }
@keyframes bootSquare { from { transform: translate(-50%,-50%) scale(1.7); opacity: 0; } to { transform: translate(-50%,-50%) scale(1); opacity: 1; } }
@keyframes bootDiamond { 0% { transform: translate(-50%,-50%) scale(0) rotate(0deg); opacity: 0; } 60% { transform: translate(-50%,-50%) scale(1.2) rotate(45deg); opacity: 1; } 100% { transform: translate(-50%,-50%) scale(1) rotate(45deg); opacity: 1; } }
@keyframes bootWord { from { letter-spacing: 0.55em; opacity: 0; filter: blur(8px); } to { letter-spacing: 0.2em; opacity: 1; filter: blur(0); } }
@keyframes bootCoord { from { opacity: 0; transform: translate(-50%, 6px); } to { opacity: 1; transform: translate(-50%, 0); } }
@keyframes bootOut { 0%, 74% { opacity: 1; transform: translateY(0); } 100% { opacity: 0; transform: translateY(-100%); visibility: hidden; } }

.sm-boot { position: fixed; inset: 0; z-index: 9999; overflow: hidden; background: #0a0a0c; pointer-events: none; animation: bootOut 0.5s cubic-bezier(0.7,0,0.84,0) 0.82s forwards; }
.sm-boot::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 2px; background: var(--red); }
.sm-boot-grid { position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px); background-size: 44px 44px; animation: bootGrid 1.3s ease forwards; }
.sm-boot-cross-h { position: absolute; left: 0; right: 0; top: 50%; height: 1px; background: var(--red); transform-origin: center; animation: bootCrossH 0.4s cubic-bezier(0.16,1,0.3,1) 0.05s both; }
.sm-boot-cross-v { position: absolute; top: 0; bottom: 0; left: 50%; width: 1px; background: var(--red); transform-origin: center; animation: bootCrossV 0.4s cubic-bezier(0.16,1,0.3,1) 0.05s both; }
.sm-boot-square { position: absolute; left: 50%; top: 50%; border: 1px solid var(--line-2); animation: bootSquare 0.45s cubic-bezier(0.16,1,0.3,1) both; }
.sm-boot-square.s1 { width: 300px; height: 300px; animation-delay: 0.12s; }
.sm-boot-square.s2 { width: 190px; height: 190px; animation-delay: 0.2s; }
.sm-boot-square.s3 { width: 90px; height: 90px; border-color: var(--red); animation-delay: 0.28s; }
.sm-boot-diamond { position: absolute; left: 50%; top: 50%; width: 46px; height: 46px; border: 1px solid var(--red); animation: bootDiamond 0.4s cubic-bezier(0.16,1,0.3,1) 0.34s both; }
.sm-boot-word { position: absolute; left: 50%; top: calc(50% + 195px); transform: translateX(-50%); font-family: 'Space Grotesk', sans-serif; font-size: 1.4rem; font-weight: 700; letter-spacing: 0.2em; color: var(--ink); text-align: center; white-space: nowrap; animation: bootWord 0.4s cubic-bezier(0.16,1,0.3,1) 0.42s both; }
.sm-boot-word span { color: var(--red); }
.sm-boot-coord { position: absolute; left: 50%; top: calc(50% + 232px); transform: translateX(-50%); font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.18em; color: var(--muted); white-space: nowrap; animation: bootCoord 0.35s ease 0.5s both; }

@media (prefers-reduced-motion: reduce) {
  .sm-boot { animation: none !important; opacity: 0 !important; visibility: hidden !important; }
  .sm-boot * { animation: none !important; }
}

/* major profile accordion */
.sm-major-list { margin-top: 4px; }
.sm-major { border: 1px solid var(--line); border-left: 2px solid var(--blue); background: var(--surface); margin-bottom: 8px; }
details.sm-major[open] { border-left-color: var(--red); }
.sm-major-head { display: flex; align-items: baseline; gap: 14px; cursor: pointer; list-style: none; padding: 12px 16px; }
summary.sm-major-head::-webkit-details-marker { display: none; }
.sm-major-idx { font-family: 'IBM Plex Mono', monospace; color: var(--faint); font-size: 0.72rem; }
.sm-major-name { font-family: 'Space Grotesk', sans-serif; font-size: 1.05rem; font-weight: 600; color: var(--ink); letter-spacing: 0.02em; }
.sm-major-hint { margin-left: auto; font-family: 'IBM Plex Mono', monospace; color: var(--faint); font-size: 0.68rem; letter-spacing: 0.05em; }
.sm-major-head::after { content: "[+]"; color: var(--red); font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; margin-left: 4px; }
details.sm-major[open] .sm-major-head::after { content: "[−]"; }
.sm-major-body { padding: 0 16px 18px; }
details.sm-major[open] .sm-major-body { animation: majorReveal 0.34s cubic-bezier(0.16,1,0.3,1) both; }
@keyframes majorReveal {
  from { opacity: 0; clip-path: inset(0 100% 0 0); transform: translateX(-10px); }
  to   { opacity: 1; clip-path: inset(0 0 0 0); transform: translateX(0); }
}
.sm-major-why { font-family: 'IBM Plex Mono', monospace; color: var(--muted); font-size: 0.8rem; line-height: 1.65; margin: 4px 0 12px; max-width: 62ch; }
.sm-major-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 6px 0; }
.sm-mtag-lbl { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--faint); margin-right: 2px; }
.sm-mtag { font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; letter-spacing: 0.03em; padding: 2px 8px; border: 1px solid var(--line-2); color: var(--muted); }
.sm-mtag.hi { border-color: rgba(217,119,110,0.5); color: var(--red); }
.sm-mtag.lo { border-color: var(--line); color: var(--faint); }
.sm-mtag.tier { border-color: rgba(125,155,198,0.5); color: var(--blue); }
@media (prefers-reduced-motion: reduce) { details.sm-major[open] .sm-major-body { animation: none !important; } }

/* report / flag labels */
.sm-flag-tag { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.04em; color: var(--red); border: 1px solid rgba(217,119,110,0.55); padding: 1px 7px; margin-left: 8px; vertical-align: middle; white-space: nowrap; }
.sm-flag-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 8px 12px; border: 1px solid var(--line); border-left: 2px solid var(--red); margin-bottom: 8px; }
.sm-flag-name { font-family: 'Space Grotesk', sans-serif; font-weight: 600; color: var(--ink); }

/* team analysis */
.sm-team-reveal { animation: majorReveal 0.4s cubic-bezier(0.16,1,0.3,1) both; }
[data-testid="stSpinner"] {
  position: fixed; inset: 0; z-index: 9998;
  background-color: rgba(10,10,12,0.94);
  background-image: linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 44px 44px;
  display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 18px;
  border: 1px solid var(--line);
}
[data-testid="stSpinner"]::before {
  content: ""; position: absolute; left: 50%; top: 50%;
  width: 150px; height: 150px; margin: -75px 0 0 -75px;
  border: 1px solid var(--red);
  animation: loadSpin 2.4s linear infinite;
}
[data-testid="stSpinner"]::after {
  content: ""; position: absolute; left: 50%; top: 50%;
  width: 72px; height: 72px; margin: -36px 0 0 -36px;
  border: 1px solid var(--blue);
  animation: loadSpinRev 3.2s linear infinite;
}
@keyframes loadSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes loadSpinRev { from { transform: rotate(45deg); } to { transform: rotate(405deg); } }
[data-testid="stSpinner"] > div { font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.14em; font-size: 0.82rem; color: var(--blue); text-align: center; text-transform: uppercase; }

/* geometric ping feedback */
.sm-ping { position: fixed; inset: 0; z-index: 9999; pointer-events: none; display: flex; align-items: center; justify-content: center; animation: pingFade 0.7s ease-out forwards; }
@keyframes pingFade { 0% { opacity: 0; } 15% { opacity: 1; } 100% { opacity: 0; visibility: hidden; } }
.sm-ping-cross-h { position: absolute; left: 0; right: 0; top: 50%; height: 1px; background: var(--red); animation: pingH 0.4s cubic-bezier(0.16,1,0.3,1) both; }
.sm-ping-cross-v { position: absolute; top: 0; bottom: 0; left: 50%; width: 1px; background: var(--red); animation: pingV 0.4s cubic-bezier(0.16,1,0.3,1) both; }
@keyframes pingH { from { transform: scaleX(0); opacity: 0; } to { transform: scaleX(1); opacity: 1; } }
@keyframes pingV { from { transform: scaleY(0); opacity: 0; } to { transform: scaleY(1); opacity: 1; } }
.sm-ping-square { position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%); border: 1px solid var(--red); animation: pingSq 0.45s cubic-bezier(0.16,1,0.3,1) both; }
.sm-ping-square.s1 { width: 200px; height: 200px; }
.sm-ping-square.s2 { width: 90px; height: 90px; animation-delay: 0.06s; }
@keyframes pingSq { from { transform: translate(-50%,-50%) scale(1.8); opacity: 0; } to { transform: translate(-50%,-50%) scale(1); opacity: 1; } }
.sm-ping-text { font-family: 'Space Grotesk', sans-serif; font-size: 1.4rem; font-weight: 700; letter-spacing: 0.2em; color: var(--red); animation: pingFade 0.7s ease-out both; }
@media (prefers-reduced-motion: reduce) { .sm-ping { display: none; } }
</style>

<div class="sm-header">
  <div class="sm-logo">SMART <span class="accent">MATCH</span></div>
  <div class="sm-sub">AI teammate recommendation for HKUST group projects</div>
</div>
<div class="sm-rule"></div>
'''.replace("AI teammate recommendation for HKUST group projects", t("header_sub")), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# View routing
# ---------------------------------------------------------------------------
if "view" not in st.session_state:
    st.session_state.view = "intro"

# --- collapsible left navigation ---
with st.sidebar:
    st.markdown("### SMART MATCH")
    st.selectbox("🌐 Language", list(LANG_OPTIONS.keys()), key="lang")
    st.caption(t("nav_title"))
    st.divider()
    for _label, _view in [
        (t("nav_home"), "intro"),
        (t("nav_questionnaire"), "form"),
        (t("nav_team"), "team"),
        (t("nav_database"), "library"),
        (t("nav_profiles"), "profiles"),
        (t("nav_logic"), "logic"),
        (t("nav_feedback"), "comments"),
        (t("nav_report"), "report"),
    ]:
        if st.button(_label, use_container_width=True, key=f"nav_{_view}"):
            st.session_state.view = _view
            st.rerun()

if st.session_state.view == "intro":
    # --- title screen ---
    if not st.session_state.get("boot_played"):
        st.markdown(boot_overlay(), unsafe_allow_html=True)
        st.session_state.boot_played = True
    st.markdown(intro_hero(), unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        if st.button(t("start_matching"), type="primary", use_container_width=True, key="start"):
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
    greedy = fix_team_gender(greedy_team([cand for _, cand, _ in ranked], need), [cand for _, cand, _ in ranked], user.get("gender"))
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
    if not _gender_valid([user.get("gender")] + [c.get("gender") for c in picked_cands]):
        st.warning("This team leaves a lone male/female member — consider swapping to keep them from being isolated.")

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

elif st.session_state.view == "profiles":
    # --- major 7-axis profile summary ---
    st.markdown(section("00", "Major Profiles"), unsafe_allow_html=True)
    st.caption("Click a major to reveal its 7-axis profile and why the values are set that way.")
    st.markdown(major_profiles_html(), unsafe_allow_html=True)

elif st.session_state.view == "logic":
    # --- how the matching works ---
    st.markdown(section("00", "How It Works"), unsafe_allow_html=True)
    st.markdown(
        "Matching runs in **two stages + one AI layer**:\n\n"
        "1. **TOPSIS ranking** — score every candidate on five weighted dimensions, then rank them.\n"
        "2. **Greedy team assembly** — pick teammates that together maximize seven-axis skill coverage, then fix gender balance.\n"
        "3. **AI analysis** — explain each recommendation (and, in Team Analysis, the whole team).\n\n"
        "Every formula and its source is below."
    )

    st.markdown(section("01", "Candidate 7-axis skill profile"), unsafe_allow_html=True)
    st.markdown(
        "Each candidate's skill radar (Code, Writing, Speaking, Planning, Data, Design, Leadership) is built as:\n\n"
        "```\noffset        = round((admission_tier + entry_barrier) × 1.5)\n"
        "profile[axis] = clamp( base_major[axis] + offset, 30, 95 )\n"
        "stats[axis]   = clamp( profile[axis] + jitter(±8), 30, 95 )\n"
        "             + 22 for each self-reported role that maps to that axis\n```\n\n"
        "`base_major` is a hand-tuned 0–100 prior per HKUST major (its typical learning content); `admission_tier` and "
        "`entry_barrier` are per-major offsets from JUPAS competitiveness and entry difficulty. This is a *domain-knowledge "
        "prior*, not a learned model."
    )

    st.markdown(section("02", "Ordinal similarity"), unsafe_allow_html=True)
    st.markdown(
        "For ordered multiple-choice answers (hours, grade, deadline, reliability), a linear distance similarity is used:\n\n"
        "```\nordinal(a, b) = 1                                  if a == b\n"
        "               = max(0, 1 − |pos(a) − pos(b)| / (n − 1))  otherwise\n```\n\n"
        "Adjacent options score highest; the two extremes score 0. (Idea from rank correlation — see Spearman below.)"
    )

    st.markdown(section("03", "Five matching dimensions"), unsafe_allow_html=True)
    st.markdown(
        "Each candidate is scored 0–1 on five criteria (let *my* = you, *their* = candidate):\n\n"
        "**1. Skills (complementarity)** — do they cover roles/skills I lack, without duplicating me?\n"
        "```\nrole_score  = max(0, |their_roles − my_roles| / |their_roles|\n"
        "                     − 0.5 × |their_roles ∩ my_roles| / |their_roles|)\n"
        "skill_score = same formula over 'strong axes' (role axes + major axes ≥ 60)\n"
        "Skills      = 0.6 × role_score + 0.4 × skill_score\n```\n\n"
        "**2. Availability** — meeting overlap + weekly commitment.\n"
        "```\ntime_score   = |my_meeting ∩ their_meeting| / max(|my_meeting ∪ their_meeting|, 1)   (Jaccard)\n"
        "hours_score  = ordinal(my_hours, their_hours)\n"
        "load_penalty = 0.1 if they have internship / part-time / job-hunting\n"
        "Availability = max(0, 0.6 × time_score + 0.4 × hours_score − load_penalty)\n```\n\n"
        "**3. Working style** — discussion, decision and deadline habits.\n"
        "```\nWorking style = ( [discussion match ? 1 : 0] + [decision match ? 1 : 0]\n"
        "                + ordinal(my_deadline, their_deadline) ) / 3\n```\n\n"
        "**4. Goals** — target grade and expectations.\n"
        "```\nGoals = 0.5 × ordinal(my_grade, their_grade)\n"
        "      + 0.5 × ( [expectations match ? 1 : 0.5] )\n```\n\n"
        "**5. Reliability** — delivery punctuality.\n"
        "```\nReliability = ordinal(my_reliability, their_reliability)\n```"
    )

    st.markdown(section("04", "Priority weights"), unsafe_allow_html=True)
    st.markdown(
        "Your five sliders (each 0–100) are normalized to sum to 1:\n\n"
        "```\nnormalized_w[k] = w[k] / (w[Skills] + w[Availability] + w[Working style] + w[Goals] + w[Reliability])\n```"
    )

    st.markdown(section("05", "TOPSIS ranking"), unsafe_allow_html=True)
    st.markdown(
        "TOPSIS (*Technique for Order of Preference by Similarity to Ideal Solution*) ranks candidates by closeness to an "
        "ideal best and distance from an anti-ideal worst:\n\n"
        "```\n1. vector normalize:  n_j = sqrt( Σ_i r_ij² )            (r_ij = criterion j of candidate i)\n"
        "2. weight:            v_ij = (r_ij / n_j) × w_j\n"
        "3. ideal best/worst:  A+_j = max_i v_ij ;  A−_j = min_i v_ij\n"
        "4. distances:         S+_i = sqrt( Σ_j (v_ij − A+_j)² )\n"
        "                      S−_i = sqrt( Σ_j (v_ij − A−_j)² )\n"
        "5. closeness:         C_i = S−_i / (S+_i + S−_i)\n```\n\n"
        "Rank by `C_i` descending (0–1, higher = better)."
    )

    st.markdown(section("06", "Greedy team assembly"), unsafe_allow_html=True)
    st.markdown(
        "From the ranked pool, pick teammates that **maximize seven-axis coverage** (each axis takes the team maximum):\n\n"
        "```\ncoverage_gain(candidate) = Σ_axis max(0, candidate[axis] − covered[axis])\n"
        "repeat: add the candidate with the highest gain, then update covered[axis] = max(covered[axis], candidate[axis])\n```\n\n"
        "This is the *maximum-coverage* problem (submodular); greedy guarantees a **1 − 1/e ≈ 63%** approximation.\n\n"
        "A final **gender-balance** pass swaps members so no gender is a lone member (count ≠ 1) — each gender is either "
        "absent or has ≥ 2 people, preventing isolation."
    )

    st.markdown(section("07", "References"), unsafe_allow_html=True)
    st.markdown(
        "- **TOPSIS** — Hwang & Yoon (1981), *Multiple Attribute Decision Making*. [DOI](https://doi.org/10.1007/978-3-642-48318-9)\n"
        "- **Team formation** — Lappas, Liu & Terzi (2009), *Finding a Team of Experts in Social Networks*, KDD. [DOI](https://dl.acm.org/doi/10.1145/1557019.1557074)\n"
        "- **Greedy 1−1/e bound** — Nemhauser, Wolsey & Fisher (1978), *Mathematical Programming*. [DOI](https://doi.org/10.1007/BF01588971)\n"
        "- **Team roles / complementarity** — Belbin (1981), *Management Teams*. [Site](https://www.belbin.com/about/belbin-team-roles/)\n"
        "- **Team effectiveness** — Mathieu et al. (2008), *Journal of Management*. [DOI](https://doi.org/10.1177/0149206308316061)\n"
        "- **Psychological safety** — Edmondson (1999), *Administrative Science Quarterly*. [DOI](https://doi.org/10.2307/2666999)\n"
        "- **Big Five in teamwork** — Salas, Sims & Burke (2005), *Small Group Research*. [DOI](https://doi.org/10.1177/1046496405277134)\n"
        "- **Jaccard similarity** — Jaccard (1912), *New Phytologist*. [DOI](https://doi.org/10.1111/j.1469-8137.1912.tb05611.x)\n"
        "- **Rank correlation** — Spearman (1904), *American Journal of Psychology*. [DOI](https://doi.org/10.2307/1412159)"
    )

elif st.session_state.view == "comments":
    # --- feedback / comments ---
    st.markdown(section("00", "Feedback"), unsafe_allow_html=True)
    st.caption("Comments and suggestions about the questionnaire or the site — stored anonymously.")
    c_author = st.text_input("Your name (optional)", key="c_author")
    c_body = st.text_area("Comment / suggestion", key="c_body")
    if st.button("Submit comment", type="primary", use_container_width=True):
        if not c_body.strip():
            st.warning("Please write a comment first.")
        elif save_comment((c_author or "Anonymous").strip(), c_body.strip()):
            st.success("Thanks — your comment has been posted.")
        else:
            st.warning("Couldn't reach the database (check Supabase setup).")
    st.divider()
    comments = fetch_comments()
    if not comments:
        st.caption("No comments yet — be the first.")
    else:
        for c in comments:
            st.markdown(f"**{c['author']}** · *{c['created_at'][:10]}*  \n{c['body']}", unsafe_allow_html=True)

elif st.session_state.view == "report":
    # --- report a teammate ---
    st.markdown(section("00", "Report a Teammate"), unsafe_allow_html=True)
    st.caption("Two approved reports mark a teammate; two later praises clear the mark. Evidence is reviewed by AI.")
    r_target = st.text_input("Teammate's name (as shown in the app)", key="r_target")
    r_label = st.selectbox("Label", REPORT_LABELS, key="r_label")
    r_file = st.file_uploader("Evidence file (txt / md / csv / log / json)", type=["txt", "md", "csv", "log", "json"], key="r_file")
    r_text = st.text_area("Or paste evidence (chat log / context)", key="r_text", height=120)
    if st.button("Submit for AI review", type="primary", use_container_width=True):
        evidence = ""
        if r_file is not None:
            try:
                evidence += r_file.getvalue().decode("utf-8", errors="ignore")
            except Exception:
                pass
        evidence = (evidence + "\n" + r_text).strip()
        if not r_target.strip():
            st.warning("Please enter the teammate's name.")
        elif not evidence:
            st.warning("Please attach evidence (a file or pasted text) for the AI to review.")
        else:
            verdict = llm_report_review(r_target.strip(), r_label, evidence)
            if save_report(r_target.strip(), r_label, evidence[:3000], verdict):
                flagged_people.clear()
                st.success(f"Submitted — AI verdict: **{verdict.upper()}**.")
            else:
                st.warning("Couldn't reach the database (check Supabase setup).")

    st.divider()
    st.markdown("### Give praise")
    p_target = st.text_input("Teammate's name", key="p_target")
    if st.button("Submit praise", type="primary", use_container_width=True):
        if not p_target.strip():
            st.warning("Please enter a name.")
        elif save_praise(p_target.strip()):
            flagged_people.clear()
            st.success("Praise recorded — thanks!")
        else:
            st.warning("Couldn't reach the database.")

    st.divider()
    st.markdown("### Currently flagged")
    flagged = flagged_people()
    if not flagged:
        st.caption("No one is currently flagged.")
    else:
        for _name, _labels in flagged.items():
            _tags = "".join(f'<span class="sm-flag-tag">{l}</span>' for l in _labels)
            st.markdown(f'<div class="sm-flag-row"><span class="sm-flag-name">{_name}</span>{_tags}</div>', unsafe_allow_html=True)

elif st.session_state.view == "team":
    # --- team analysis ---
    st.markdown(section("00", "Team Analysis"), unsafe_allow_html=True)
    st.caption("Assemble a team from the database, then ask the AI for a full strengths/weaknesses analysis.")
    pool = candidate_pool()
    all_names = [s["name"] for s in pool]
    team_pick = st.multiselect("Pick teammates from the database", all_names, key="team_pick")

    if st.button("Start teaming", type="primary", use_container_width=True):
        if not team_pick:
            st.warning("Pick at least one teammate first.")
        else:
            st.session_state.team = [s for s in pool if s["name"] in team_pick]
            st.session_state.team_formed = True
            st.session_state.team_result = None
            st.session_state.ping_label = "TEAM FORMED"
            st.rerun()

    if st.session_state.get("ping_label"):
        st.markdown(ping_overlay(st.session_state.pop("ping_label")), unsafe_allow_html=True)

    team = st.session_state.get("team") or []
    if st.session_state.get("team_formed") and team:
        st.markdown('<div class="sm-team-reveal">' + team_coverage_html(team) + '</div>', unsafe_allow_html=True)
        if st.button("Start analysis", type="primary", use_container_width=True):
            st.session_state.team_analyzing = True
            st.rerun()

    if st.session_state.get("team_analyzing"):
        _team = st.session_state.get("team") or []
        with st.spinner("ANALYZING TEAM — mapping coverage, strengths and gaps…"):
            _res = llm_analysis(_team_analysis_prompt(_team))
        st.session_state.team_result = _res
        st.session_state.team_analyzing = False
        st.rerun()

    if st.session_state.get("team_result"):
        st.markdown(team_analysis_html(st.session_state.team_result), unsafe_allow_html=True)

else:
    # --- questionnaire view ---
    if st.session_state.get("just_started"):
        st.markdown(launch_overlay(), unsafe_allow_html=True)
        st.session_state.just_started = False
    st.markdown(section("01", "About you"), unsafe_allow_html=True)
    year = st.selectbox("Year of study", ["Year 1", "Year 2", "Year 3", "Year 4"])
    gender = st.selectbox("Gender", ["Male", "Female", "Prefer not to say"])
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
    st.caption("Five sliders, each **0–100** (aligned and identical). Their total must stay **≤ 100** — a live total is shown below.")
    w_skills = st.slider("Skills complementarity", 0, 100, 0, key="uw_skills")
    w_avail = st.slider("Availability alignment", 0, 100, 0, key="uw_avail")
    w_style = st.slider("Working-style compatibility", 0, 100, 0, key="uw_style")
    w_goals = st.slider("Goals alignment", 0, 100, 0, key="uw_goals")
    w_reliab = st.slider("Reliability", 0, 100, 0, key="uw_reliab")
    _wtotal = w_skills + w_avail + w_style + w_goals + w_reliab
    if _wtotal <= 100:
        st.caption(f"Allocated **{_wtotal} / 100** — {100 - _wtotal} point(s) free.")
    else:
        st.caption(f"⚠️ **{_wtotal} / 100** — over by **{_wtotal - 100}**, reduce before submitting.")

    st.caption("By submitting, you agree that your answers are stored anonymously (under a generated name) to improve matching.")
    submitted = st.button("Find teammates", type="primary", use_container_width=True)

    if submitted:
        if not roles or not meeting:
            st.warning("Please pick at least one role and one meeting time.")
        elif _wtotal == 0:
            st.warning("Please allocate at least a few points across the five priority dimensions.")
        elif _wtotal > 100:
            st.error(f"The five priorities total {_wtotal}, but they must not exceed 100. Reduce some sliders.")
        else:
            st.session_state.user = {
                "course": course, "roles": roles, "hours": hours, "meeting": meeting,
                "load": load, "grade": grade, "expect": expect,
                "discussion": discussion, "decision": decision, "deadline": deadline,
                "reliability": reliability,
                "year": year, "major": major, "gender": gender,
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
