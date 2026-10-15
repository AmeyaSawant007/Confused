"""Decision categories, starter criteria and ready-made demo templates."""
from __future__ import annotations

CATEGORIES = [
    {"id": "career", "label": "Career", "icon": "💼",
     "blurb": "Which path grows your career fastest?",
     "suggested_criteria": [
         {"name": "Growth", "type": "benefit"},
         {"name": "Salary", "type": "benefit"},
         {"name": "Work-life balance", "type": "benefit"},
         {"name": "Stress", "type": "cost"},
         {"name": "Location fit", "type": "benefit"}]},
    {"id": "college", "label": "College / Course", "icon": "🎓",
     "blurb": "Pick the right college or course.",
     "suggested_criteria": [
         {"name": "Fees (₹)", "type": "cost"},
         {"name": "Ranking", "type": "benefit"},
         {"name": "Placements (%)", "type": "benefit"},
         {"name": "Distance (km)", "type": "cost"},
         {"name": "Campus life", "type": "benefit"}]},
    {"id": "project", "label": "Project", "icon": "🛠️",
     "blurb": "Choose a final-year or side project.",
     "suggested_criteria": [
         {"name": "Learning Value", "type": "benefit"},
         {"name": "Feasibility", "type": "benefit"},
         {"name": "Novelty", "type": "benefit"},
         {"name": "Cost (₹)", "type": "cost"},
         {"name": "Placement Impact", "type": "benefit"}]},
    {"id": "gadgets", "label": "Laptop / Phone", "icon": "💻",
     "blurb": "Compare gadgets on what matters to you.",
     "suggested_criteria": [
         {"name": "Price", "type": "cost"},
         {"name": "Performance", "type": "benefit"},
         {"name": "Battery Life", "type": "benefit"},
         {"name": "Weight", "type": "cost"}]},
    {"id": "travel", "label": "Travel", "icon": "✈️",
     "blurb": "Where should you go next?",
     "suggested_criteria": [
         {"name": "Cost (₹)", "type": "cost"},
         {"name": "Safety", "type": "benefit"},
         {"name": "Fun", "type": "benefit"},
         {"name": "Travel time (hrs)", "type": "cost"},
         {"name": "Food", "type": "benefit"}]},
    {"id": "job", "label": "Job / Internship", "icon": "📄",
     "blurb": "Compare offers and internships.",
     "suggested_criteria": [
         {"name": "Stipend (₹/month)", "type": "benefit"},
         {"name": "Learning", "type": "benefit"},
         {"name": "Brand Value", "type": "benefit"},
         {"name": "Commute (min)", "type": "cost"},
         {"name": "PPO Chance (%)", "type": "benefit"}]},
    {"id": "daily", "label": "Daily Decision", "icon": "☀️",
     "blurb": "Small everyday choices, decided well.",
     "suggested_criteria": [
         {"name": "Time (min)", "type": "cost"},
         {"name": "Cost (₹)", "type": "cost"},
         {"name": "Health", "type": "benefit"},
         {"name": "Enjoyment", "type": "benefit"}]},
    {"id": "custom", "label": "Custom", "icon": "✨",
     "blurb": "Start from a blank slate.",
     "suggested_criteria": []},
]


def _c(name, weight, type="benefit"):
    return {"name": name, "weight": weight, "type": type}


def _o(name, description, scores):
    return {"name": name, "description": description, "scores": scores}


def _k(target, operator, value, name=None, hard=True):
    return {"name": name or f"{target} {operator} {value:g}",
            "target": target, "operator": operator, "value": value,
            "hard": hard, "enabled": True}


TEMPLATES = [
    {
        "id": "laptop",
        "title": "Which laptop should I buy?",
        "category": "gadgets",
        "criteria": [
            _c("Price", 30, "cost"),
            _c("Performance", 35),
            _c("Battery Life", 20),
            _c("Weight", 15, "cost"),
        ],
        "options": [
            _o("AeroBook 14", "Balanced 14-inch ultrabook.",
               {"Price": 72000, "Performance": 7, "Battery Life": 14, "Weight": 1.4}),
            _o("Titan Gaming 15", "Heavy performance machine.",
               {"Price": 79000, "Performance": 10, "Battery Life": 6, "Weight": 2.3}),
            _o("EcoLite 13", "Light, affordable, long battery.",
               {"Price": 55000, "Performance": 5, "Battery Life": 18, "Weight": 1.2}),
        ],
        "constraints": [
            _k("Price", "<=", 80000, "Budget ≤ ₹80,000"),
            _k("Weight", "<=", 2.0, "Weight ≤ 2 kg"),
        ],
    },
    {
        "id": "project",
        "title": "Which final-year project should I choose?",
        "category": "project",
        "criteria": [
            _c("Learning Value", 25),
            _c("Feasibility", 20),
            _c("Novelty", 15),
            _c("Cost (₹)", 10, "cost"),
            _c("Placement Impact", 15),
            _c("Build Time (weeks)", 15, "cost"),
        ],
        "options": [
            _o("AI Attendance System", "CV-based classroom attendance.",
               {"Learning Value": 7, "Feasibility": 9, "Novelty": 5,
                "Cost (₹)": 8000, "Placement Impact": 7, "Build Time (weeks)": 10}),
            _o("Confused? Decision Platform", "This very decision-support app.",
               {"Learning Value": 9, "Feasibility": 7, "Novelty": 8,
                "Cost (₹)": 2000, "Placement Impact": 8, "Build Time (weeks)": 12}),
            _o("IoT Smart Irrigation", "Sensor-driven farm watering.",
               {"Learning Value": 8, "Feasibility": 5, "Novelty": 9,
                "Cost (₹)": 25000, "Placement Impact": 6, "Build Time (weeks)": 20}),
        ],
        "constraints": [
            _k("Cost (₹)", "<=", 15000, "Budget ≤ ₹15,000"),
            _k("Build Time (weeks)", "<=", 16, "Finish in ≤ 16 weeks"),
        ],
    },
    {
        "id": "internship",
        "title": "Which internship should I accept?",
        "category": "job",
        "criteria": [
            _c("Stipend (₹/month)", 25),
            _c("Learning", 30),
            _c("Brand Value", 15),
            _c("Commute (min)", 15, "cost"),
            _c("PPO Chance (%)", 15),
        ],
        "options": [
            _o("Startup SDE Intern", "Fast-moving product startup.",
               {"Stipend (₹/month)": 30000, "Learning": 9, "Brand Value": 5,
                "Commute (min)": 20, "PPO Chance (%)": 40}),
            _o("Bank IT Intern", "Big-brand enterprise IT.",
               {"Stipend (₹/month)": 50000, "Learning": 5, "Brand Value": 8,
                "Commute (min)": 60, "PPO Chance (%)": 70}),
            _o("Remote ML Intern", "Work-from-home ML role.",
               {"Stipend (₹/month)": 20000, "Learning": 8, "Brand Value": 6,
                "Commute (min)": 0, "PPO Chance (%)": 30}),
        ],
        "constraints": [
            _k("Commute (min)", "<=", 45, "Commute ≤ 45 min"),
            _k("Stipend (₹/month)", ">=", 15000, "Stipend ≥ ₹15,000"),
        ],
    },
    {
        "id": "tech",
        "title": "Which technology should I learn next?",
        "category": "career",
        "criteria": [
            _c("Job Demand", 25),
            _c("Salary Potential", 20),
            _c("Learning Speed", 15),
            _c("Fun Factor", 10),
            _c("Free Resources", 10),
            _c("Time to Job-Ready (months)", 20, "cost"),
        ],
        "options": [
            _o("React & Frontend", "UI engineering with React.",
               {"Job Demand": 8, "Salary Potential": 7, "Learning Speed": 9,
                "Fun Factor": 7, "Free Resources": 10,
                "Time to Job-Ready (months)": 3}),
            _o("ML & Deep Learning", "AI/ML engineering path.",
               {"Job Demand": 9, "Salary Potential": 10, "Learning Speed": 5,
                "Fun Factor": 8, "Free Resources": 9,
                "Time to Job-Ready (months)": 8}),
            _o("Go & Backend", "Backend systems with Go.",
               {"Job Demand": 7, "Salary Potential": 8, "Learning Speed": 6,
                "Fun Factor": 6, "Free Resources": 7,
                "Time to Job-Ready (months)": 4}),
            _o("Flutter & Mobile", "Cross-platform mobile apps.",
               {"Job Demand": 6, "Salary Potential": 6, "Learning Speed": 7,
                "Fun Factor": 9, "Free Resources": 8,
                "Time to Job-Ready (months)": 4}),
        ],
        "constraints": [
            _k("Time to Job-Ready (months)", "<=", 6, "Job-ready in ≤ 6 months"),
        ],
    },
]

TEMPLATE_INDEX = {t["id"]: t for t in TEMPLATES}
