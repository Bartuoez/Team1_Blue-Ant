import json
import streamlit as st
import requests

# =========================
# Seitenkonfiguration
# =========================
st.set_page_config(
    page_title="Blue Ant Projektanalyse",
    layout="wide"
)

st.title("📊 Plan- vs. Ist-Aufwand – Projektanalyse (KI-gestützt)")

# =========================
# Daten laden
# =========================
@st.cache_data
def load_data():
    try:
        with open("backend/blueant_combined_20260118_184540.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("❌ Kombinierte JSON-Datei nicht gefunden.")
        return []

raw_data = load_data()

# =========================
# Projektdaten aufbereiten
# =========================
projects = {}

for entry in raw_data:
    project_info = entry.get("project_data", {}).get("project", {})
    kpis = entry.get("kpis", {}).get("kpis", [])

    project_name = project_info.get("name", "Unbekannt")
    project_number = project_info.get("number", "-")
    project_key = f"{project_name} ({project_number})"

    work_actual = 0.0
    work_plan = 0.0

    for kpi in kpis:
        if kpi.get("period") == "TOTAL":
            if kpi.get("id") == "WorkTotalActual":
                work_actual = kpi.get("value", 0.0)
            elif kpi.get("id") == "WorkTotalPlan":
                work_plan = kpi.get("value", 0.0)

    variance = work_actual - work_plan
    variance_pct = (variance / work_plan * 100) if work_plan > 0 else 0.0

    projects[project_key] = {
        "Ist": round(work_actual, 2),
        "Plan": round(work_plan, 2),
        "Abweichung": round(variance, 2),
        "Abweichung_pct": round(variance_pct, 2)
    }

# =========================
# Projekt auswählen
# =========================
st.subheader("📌 Projekt auswählen")

if not projects:
    st.warning("Keine Projekte verfügbar.")
    st.stop()

selected_project = st.selectbox(
    "Projekt",
    options=sorted(projects.keys())
)

project_data = projects[selected_project]

# =========================
# Kennzahlen anzeigen
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Ist-Aufwand (h)", f"{project_data['Ist']} h")
col2.metric("Plan-Aufwand (h)", f"{project_data['Plan']} h")
col3.metric(
    "Abweichung (h)",
    f"{project_data['Abweichung']} h",
    delta=f"{project_data['Abweichung_pct']} %",
    delta_color="inverse"
)

# =========================
# OLLAMA / LLAMA3 KI-ANALYSE
# =========================
def llama3_analysis(project_name, plan, actual, variance, variance_pct):
    prompt = f"""
Du bist ein Projektcontrolling-Experte.
Analysiere kurz und präzise die Plan-vs-Ist-Abweichung.

Projekt: {project_name}
Geplanter Aufwand: {plan} Stunden
Tatsächlicher Aufwand: {actual} Stunden
Abweichung: {variance} Stunden ({variance_pct:.2f} %)

Erstelle:
- eine kurze Bewertung
- eine mögliche Ursache
- eine konkrete Empfehlung

Antworte sachlich, professionell und kompakt.
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        },
        timeout=60
    )

    response.raise_for_status()
    return response.json()["response"]

# =========================
# Analyse anzeigen
# =========================
st.divider()
st.subheader("🤖 KI-Analyse (llama3)")

if st.button("KI-Analyse erzeugen"):
    with st.spinner("🧠 Llama 3 analysiert das Projekt..."):
        try:
            analysis_text = llama3_analysis(
                project_name=selected_project,
                plan=project_data["Plan"],
                actual=project_data["Ist"],
                variance=project_data["Abweichung"],
                variance_pct=project_data["Abweichung_pct"]
            )
            st.success("Analyse abgeschlossen")
            st.write(analysis_text)

        except Exception as e:
            st.error(f"❌ Fehler bei der KI-Analyse: {e}")
