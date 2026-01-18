import json
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
from datetime import datetime, timedelta

# =========================
# Konfiguration
# =========================
st.set_page_config(
    page_title="Blue Ant Projekt-Controlling",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS für besseres Design
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .critical-alert {
        background: #ff4444;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #cc0000;
    }
    .success-alert {
        background: #00C851;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #007E33;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<h1 class="main-header">📊 Blue Ant Projekt-Controlling & KI-Analyse</h1>',
    unsafe_allow_html=True
)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

# =========================
# Daten laden
# =========================
@st.cache_data
def load_data():
    with open("backend/blueant_combined_20260118_184540.json", "r", encoding="utf-8") as f:
        return json.load(f)

raw_data = load_data()

# =========================
# Hilfsfunktionen
# =========================
def call_llama(prompt: str) -> str:
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=90
        )
        r.raise_for_status()
        return r.json()["response"]
    except Exception as e:
        return f"⚠️ KI-Fehler: {e}"

# =========================
# ❗❗❗ PROJEKTE AUFBEREITEN – HIER WAR DER FEHLER ❗❗❗
# =========================
projects = []
status_counter = Counter()


def get_status_color(status_name: str) -> str:
    """Gibt eine Farbe für den Projektstatus zurück"""
    colors = {
        "Abgeschlossen": "#00C851",
        "In Bearbeitung": "#33b5e5",
        "Geplant": "#ffbb33",
        "On Hold": "#ff4444",
        "Abgebrochen": "#aa66cc",
        "Unbekannt": "#78909c"
    }
    return colors.get(status_name, "#78909c")

def get_ampel_color(ampel: str) -> str:
    """Gibt Farbe für Statusampel zurück"""
    if not ampel:
        return "#78909c"  # Grau (Fallback)

    ampel = ampel.upper()

    colors = {
        "GRUEN": "#00C851",
        "GELB": "#ffbb33",
        "ROT": "#ff4444",
        "GRAU": "#78909c"
    }

    return colors.get(ampel, "#78909c")


for entry in raw_data:
    # ✅ ZUERST Daten aus JSON holen
    project_data = entry.get("project_data", {}).get("project", {})
    kpis_data = entry.get("kpis", {})
    planningentries = entry.get("planningentries", {})
    status_info = entry.get("status_info", {})

    # =========================
    # Meilensteine bestimmen
    # (Planning Entries ohne Type)
    # =========================
    milestones = []

    for pe in planningentries.get("planningEntries", []):
        pe_type = pe.get("type")

        if pe_type is None or pe_type == "":
            planned = pe.get("plannedWork", 0)
            actual = pe.get("actualWork", 0)

            progress_ms = (actual / planned * 100) if planned > 0 else 0

            milestones.append({
                "name": pe.get("description", "Meilenstein"),
                "start": pe.get("start"),
                "end": pe.get("end"),
                "plannedWork": planned,
                "actualWork": actual,
                "progress": round(progress_ms, 1)
            })

    # =========================
    # Projektdaten
    # =========================
    name = project_data.get("name", "Unbekannt")
    number = project_data.get("number", "-")

    # Status
    status_name = status_info.get("name", "Unbekannt")
    status_counter[status_name] += 1

    # =========================
    # KPIs
    # =========================
    work_plan = 0.0
    work_actual = 0.0

    for kpi in kpis_data.get("kpis", []):
        if kpi.get("period") == "TOTAL":
            if kpi.get("id") == "WorkTotalPlan":
                work_plan = kpi.get("value", 0.0)
            elif kpi.get("id") == "WorkTotalActual":
                work_actual = kpi.get("value", 0.0)

    # Fortschritt
    progress = (work_actual / work_plan * 100) if work_plan > 0 else 0.0

    # =========================
    # Statusampel aus Fortschritt
    # =========================
    if progress >= 90:
        ampel = "GRUEN"
    elif progress >= 50:
        ampel = "GELB"
    elif progress > 0:
        ampel = "ROT"
    else:
        ampel = "GRAU"

    # =========================
    # Projekt sammeln
    # =========================
    projects.append({
        "key": f"{name} ({number})",
        "name": name,
        "number": number,
        "plan": work_plan,
        "actual": work_actual,
        "variance": work_actual - work_plan,
        "progress": progress,
        "status": status_name,
        "ampel": ampel,
        "milestones": milestones,
        "status_text": project_data.get("statusMemo", ""),
        "subject_text": project_data.get("subjectMemo", ""),
        "start_date": project_data.get("start"),
        "end_date": project_data.get("end"),
        "project_id": project_data.get("id")
    })
# =========================
# Sidebar - Filter
# =========================
with st.sidebar:
    st.header("Filter & Einstellungen")

    st.subheader("Direktauswahl")

    all_project_keys = [p["key"] for p in projects]

    selected_project_sidebar = st.selectbox(
        "Springe zu Projekt",
        options=["-- Alle Projekte --"] + all_project_keys,
        help="Wähle ein spezifisches Projekt für die Detailanalyse"
    )

    st.divider()

    status_filter = st.multiselect(
        "Projektstatus filtern",
        options=list(status_counter.keys()),
        default=list(status_counter.keys())
    )

    ampel_filter = st.multiselect(
        "Statusampel filtern",
        options=["GRUEN", "GELB", "ROT", "GRAU"],
        default=["GRUEN", "GELB", "ROT", "GRAU"]
    )

    st.divider()
    show_critical_only = st.checkbox("Nur kritische Projekte anzeigen", value=False)

    st.divider()
    st.info("**Tipp:** Nutze die Filter, um spezifische Projektgruppen zu analysieren.")

filtered_projects = [
    p for p in projects
    if p["status"] in status_filter
       and p["ampel"] in ampel_filter
]

if selected_project_sidebar != "-- Alle Projekte --":
    show_overview = False
    selected_project_key = selected_project_sidebar
else:
    show_overview = True
    selected_project_key = None

# =========================
# Dashboard Übersicht
# =========================
st.header("  Portfolio-Übersicht")

col1, col2, col3, col4 = st.columns(4)

total_projects = len(filtered_projects)
total_plan = sum(p["plan"] for p in filtered_projects)
total_actual = sum(p["actual"] for p in filtered_projects)
avg_progress = sum(p["progress"] for p in filtered_projects) / total_projects if total_projects > 0 else 0

col1.metric("Projekte gesamt", total_projects, help="Anzahl gefilterter Projekte")
col2.metric("Plan-Aufwand gesamt", f"{total_plan:,.0f} h", help="Gesamter geplanter Aufwand")
col3.metric("Ist-Aufwand gesamt", f"{total_actual:,.0f} h",
            delta=f"{total_actual - total_plan:+,.0f} h", delta_color="inverse")
col4.metric("Fortschritt", f"{avg_progress:.1f}%", help="Durchschnittlicher Projektfortschritt")

st.divider()

# =========================
# Visualisierungen
# =========================
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("  Projektstatus-Verteilung")

    status_df = pd.DataFrame(list(status_counter.items()), columns=["Status", "Anzahl"])
    status_df = status_df[status_df["Status"].isin(status_filter)]

    if not status_df.empty:
        fig_status = px.pie(
            status_df,
            values="Anzahl",
            names="Status",
            color="Status",
            color_discrete_map={s: get_status_color(s) for s in status_df["Status"]},
            hole=0.4
        )
        fig_status.update_traces(textposition='inside', textinfo='percent+label')
        fig_status.update_layout(showlegend=True, height=350)
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("Keine Daten für Status-Verteilung verfügbar")

with col_right:
    st.subheader("  Statusampel-Verteilung")

    ampel_counter = Counter(p["ampel"] for p in filtered_projects)
    ampel_df = pd.DataFrame(list(ampel_counter.items()), columns=["Ampel", "Anzahl"])

    if not ampel_df.empty:
        fig_ampel = go.Figure(data=[
            go.Bar(
                x=ampel_df["Ampel"],
                y=ampel_df["Anzahl"],
                marker_color=[get_ampel_color(a) for a in ampel_df["Ampel"]],
                text=ampel_df["Anzahl"],
                textposition='auto',
            )
        ])
        fig_ampel.update_layout(
            xaxis_title="Statusampel",
            yaxis_title="Anzahl Projekte",
            showlegend=False,
            height=350
        )
        st.plotly_chart(fig_ampel, use_container_width=True)
    else:
        st.info("Keine Daten für Ampel-Verteilung verfügbar")

# =========================
# Portfolio-Analyse
# =========================
st.header("  Portfolio-Analyse")

if filtered_projects:
    fig_scatter = px.scatter(
        filtered_projects,
        x="progress",
        y="variance",
        size="plan",
        color="ampel",
        hover_name="name",
        color_discrete_map={
            "GRUEN": "#00C851",
            "GELB": "#ffbb33",
            "ROT": "#ff4444",
            "GRAU": "#78909c"
        },
        labels={
            "progress": "Fortschritt (%)",
            "variance": "Abweichung (h)",
            "plan": "Plan-Aufwand",
            "ampel": "Statusampel"
        },
        title="Projektportfolio: Fortschritt vs. Abweichung"
    )
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.info("Keine Projekte für Portfolio-Analyse verfügbar")

# =========================
# Kritikalitäts-Analyse
# =========================
st.header("  Kritikalitäts-Analyse")


def assess_criticality(project):
    """Bewertet Projektkritikalität"""
    critical_reasons = []
    score = 0

    if project["ampel"] == "ROT":
        critical_reasons.append("  Statusampel Rot")
        score += 3
    elif project["ampel"] == "GELB":
        critical_reasons.append("  Statusampel Gelb")
        score += 1

    if project["progress"] < 80 and project["actual"] > project["plan"] * 0.8:
        critical_reasons.append("  Hoher Aufwand bei geringem Fortschritt")
        score += 2

    if project["plan"] > 0 and project["variance"] > project["plan"] * 0.1:
        critical_reasons.append(f"  Aufwandsüberschreitung: +{project['variance']:.0f}h")
        score += 2

    if project["status_text"]:
        critical_keywords = ["verzˆger", "risiko", "problem", "kritisch", "gefahr", "schwierig"]
        if any(word in project["status_text"].lower() for word in critical_keywords):
            critical_reasons.append("  Kritische Hinweise im Statustext")
            score += 1

    overdue_milestones = 0
    today = datetime.now()
    for ms in project["milestones"]:
        if ms["end"] and ms["progress"] < 100:
            try:
                end_str = ms["end"].replace("Z", "").replace("+00:00", "")
                if "T" in end_str:
                    end_date = datetime.fromisoformat(end_str)
                else:
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")

                if end_date < today:
                    overdue_milestones += 1
            except Exception as e:
                pass

    if overdue_milestones > 0:
        critical_reasons.append(f"  {overdue_milestones}überfällige Meilensteine")
        score += overdue_milestones

    return {
        "score": score,
        "reasons": critical_reasons,
        "is_critical": score >= 3
    }


for project in filtered_projects:
    project["criticality"] = assess_criticality(project)

critical_projects = [p for p in filtered_projects if p["criticality"]["is_critical"]]

if show_critical_only:
    display_projects = critical_projects
else:
    display_projects = filtered_projects

if critical_projects:
    st.warning(f"  **{len(critical_projects)} von {len(filtered_projects)} Projekten als kritisch eingestuft**")

    top_critical = sorted(critical_projects, key=lambda x: x["criticality"]["score"], reverse=True)[:5]

    for i, proj in enumerate(top_critical, 1):
        with st.expander(f"#{i} {proj['name']} (Kritikalität: {proj['criticality']['score']})"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Fortschritt", f"{proj['progress']:.1f}%")
            col2.metric("Abweichung", f"{proj['variance']:+.0f}h")
            col3.metric("Ampel", proj['ampel'])

            st.write("**Kritische Faktoren:**")
            for reason in proj["criticality"]["reasons"]:
                st.write(f"- {reason}")
else:
    st.success("Keine kritischen Projekte identifiziert")

st.divider()

# =========================
# Detailanalyse einzelnes Projekt
# =========================
st.header("  Projekt-Detailanalyse")

if not display_projects:
    st.warning("Keine Projekte mit den aktuellen Filtereinstellungen gefunden.")
else:
    if selected_project_key:
        project = next((p for p in projects if p["key"] == selected_project_key), None)

        if project:
            if "criticality" not in project:
                project["criticality"] = assess_criticality(project)

            st.info(f"  Ausgewähltes Projekt aus Sidebar: **{project['name']}**")
        else:
            st.error("Projekt nicht gefunden!")
            project = None
    else:
        selected_key = st.selectbox(
            "Projekt auswählen",
            options=[p["key"] for p in display_projects],
            help="Wähle ein Projekt für die Detailanalyse"
        )
        project = next(p for p in display_projects if p["key"] == selected_key)

    if project:
        col_header1, col_header2 = st.columns([3, 1])
        with col_header1:
            st.subheader(f"  {project['name']}")
            st.caption(f"Projektnummer: {project['number']} | Status: {project['status']}")
        with col_header2:
            ampel_emoji = {"GRUEN": " ", "GELB": " ", "ROT": " ", "GRAU": " "}
            st.markdown(f"### {ampel_emoji.get(project['ampel'], '?')} {project['ampel']}")

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Plan-Aufwand", f"{project['plan']:.0f}h")
        col2.metric("Ist-Aufwand", f"{project['actual']:.0f}h")
        col3.metric("Abweichung", f"{project['variance']:+.0f}h", delta_color="inverse")
        col4.metric("Fortschritt", f"{project['progress']:.1f}%")

        if project["progress"] > 0:
            forecast = project["actual"] / (project["progress"] / 100)
            forecast_variance = forecast - project["plan"]
            col5.metric("Prognose Gesamt", f"{forecast:.0f}h",
                        delta=f"{forecast_variance:+.0f}h", delta_color="inverse")
        else:
            col5.metric("Prognose Gesamt", "N/A")

        st.progress(min(project["progress"] / 100, 1.0))

        tab1, tab2, tab3, tab4 = st.tabs(["  Übersicht", "  Textzusammenfassungen", "  Meilensteine", "  KI-Analyse"])

        with tab1:
            col_a, col_b = st.columns(2)

            with col_a:
                st.subheader("  Aufwandsentwicklung")

                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=project["progress"],
                    delta={'reference': 100, 'increasing': {'color': "green"}},
                    title={'text': "Fortschritt (%)"},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': get_ampel_color(project["ampel"])},
                        'steps': [
                            {'range': [0, 33], 'color': "#ffebee"},
                            {'range': [33, 66], 'color': "#fff9c4"},
                            {'range': [66, 100], 'color': "#e8f5e9"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))
                fig_gauge.update_layout(height=300)
                st.plotly_chart(fig_gauge, use_container_width=True)

            with col_b:
                st.subheader("  Aufwandsvergleich")

                fig_bar = go.Figure(data=[
                    go.Bar(name='Plan', x=['Aufwand'], y=[project["plan"]], marker_color='#33b5e5'),
                    go.Bar(name='Ist', x=['Aufwand'], y=[project["actual"]], marker_color='#ff4444')
                ])
                fig_bar.update_layout(
                    barmode='group',
                    height=300,
                    yaxis_title="Stunden",
                    showlegend=True
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            if project["start_date"] or project["end_date"]:
                st.subheader("  Zeitplan")
                time_col1, time_col2 = st.columns(2)
                if project["start_date"]:
                    time_col1.write(f"**Start:** {project['start_date'][:10]}")
                if project["end_date"]:
                    time_col2.write(f"**Ende:** {project['end_date'][:10]}")

        with tab2:
            st.subheader("  KI-Zusammenfassungen")

            col_sum1, col_sum2 = st.columns(2)

            with col_sum1:
                with st.container(border=True):
                    st.markdown("####   Projektstatus")
                    if st.button("Status zusammenfassen", key="sum_status"):
                        with st.spinner("KI analysiert Statustext..."):
                            if project["status_text"]:
                                prompt = f"""Fasse folgenden Projektstatus in maximal 3 prägnanten Stichpunkten zusammen:

{project['status_text']}

Fokussiere auf: Aktueller Stand, Probleme, nächste Schritte."""
                                summary = call_llama(prompt)
                                st.write(summary)
                            else:
                                st.info("Kein Statustext vorhanden")

            with col_sum2:
                with st.container(border=True):
                    st.markdown("####   Projektgegenstand")
                    if st.button("Gegenstand zusammenfassen", key="sum_subject"):
                        with st.spinner("KI analysiert Projektbeschreibung..."):
                            if project["subject_text"]:
                                prompt = f"""Fasse folgenden Projektgegenstand in maximal 3 prägnanten Stichpunkten zusammen:

{project['subject_text']}

Fokussiere auf: Hauptziel, Umfang, Besonderheiten."""
                                summary = call_llama(prompt)
                                st.write(summary)
                            else:
                                st.info("Keine Projektbeschreibung vorhanden")

            with st.expander("  Originaltext Status anzeigen"):
                st.text(project["status_text"] if project["status_text"] else "Nicht vorhanden")

            with st.expander("  Originaltext Gegenstand anzeigen"):
                st.text(project["subject_text"] if project["subject_text"] else "Nicht vorhanden")

        with tab3:
            st.subheader("  Meilenstein-Übersicht")

            if project["milestones"]:
                ms_data = []
                today = datetime.now()

                for ms in project["milestones"]:
                    status = "Abgeschlossen" if ms["progress"] >= 100 else "  In Arbeit"

                    if ms["end"]:
                        try:
                            end_str = ms["end"].replace("Z", "").replace("+00:00", "")
                            if "T" in end_str:
                                end_date = datetime.fromisoformat(end_str)
                            else:
                                end_date = datetime.strptime(end_str, "%Y-%m-%d")

                            if end_date < today and ms["progress"] < 100:
                                status = "  Überfällig"
                        except:
                            pass

                    ms_data.append({
                        "Meilenstein": ms["name"],
                        "Start": ms["start"][:10] if ms["start"] else "N/A",
                        "Ende": ms["end"][:10] if ms["end"] else "N/A",
                        "Fortschritt": f"{ms['progress']}%",
                        "Status": status
                    })

                ms_df = pd.DataFrame(ms_data)
                st.dataframe(ms_df, use_container_width=True, hide_index=True)

                fig_ms = go.Figure()
                for ms in project["milestones"]:
                    color = "#00C851" if ms["progress"] >= 100 else "#ffbb33" if ms["progress"] > 0 else "#ff4444"
                    fig_ms.add_trace(go.Bar(
                        x=[ms["progress"]],
                        y=[ms["name"]],
                        orientation='h',
                        marker_color=color,
                        text=f"{ms['progress']}%",
                        textposition='auto'
                    ))

                fig_ms.update_layout(
                    xaxis_title="Fortschritt (%)",
                    xaxis_range=[0, 100],
                    showlegend=False,
                    height=max(200, len(project["milestones"]) * 50)
                )
                st.plotly_chart(fig_ms, use_container_width=True)
            else:
                st.info("Keine Meilensteine für dieses Projekt definiert")

        with tab4:
            st.subheader("  KI-Gesamtbewertung")

            if st.button("  Umfassende KI-Analyse starten", type="primary", use_container_width=True):
                with st.spinner("Llama 3 analysiert das Projekt umfassend..."):
                    # Baue umfassenden Kontext für KI
                    context = f"""Projektname: {project['name']}
Projektnummer: {project['number']}
Status: {project['status']}
Statusampel: {project['ampel']}

KENNZAHLEN:
- Plan-Aufwand: {project['plan']:.0f} Stunden
- Ist-Aufwand: {project['actual']:.0f} Stunden
- Abweichung: {project['variance']:+.0f} Stunden
- Fortschritt: {project['progress']:.1f}%

KRITIKALITƒT:
- Score: {project['criticality']['score']}
- Kritische Faktoren: {', '.join(project['criticality']['reasons']) if project['criticality']['reasons'] else 'Keine'}

MEILENSTEINE:
{len(project['milestones'])} Meilensteine definiert

STATUSTEXT:
{project['status_text'] if project['status_text'] else 'Nicht vorhanden'}

PROJEKTGEGENSTAND:
{project['subject_text'] if project['subject_text'] else 'Nicht vorhanden'}"""

                    prompt = f"""Du bist ein erfahrener Projektcontroller. Analysiere folgendes Projekt und erstelle eine umfassende Bewertung:

{context}

Erstelle eine strukturierte Analyse mit folgenden Punkten:

1. GESAMTBEWERTUNG (1-2 Sätze)
2. STƒRKEN (2-3 Punkte)
3. RISIKEN & SCHWƒCHEN (2-3 Punkte)
4. HANDLUNGSEMPFEHLUNGEN (3-4 konkrete Maﬂnahmen)
5. PROGNOSE (Kurze Einschätzung zur weiteren Entwicklung)

Sei präzise, objektiv und handlungsorientiert."""

                    analysis = call_llama(prompt)
                    st.markdown(analysis)

                    st.divider()

                    # Zusätzliche Analyse-Optionen
                    st.subheader("  Weitere Analysen")

                    col_ana1, col_ana2 = st.columns(2)

                    with col_ana1:
                        if st.button("  Risiko-Analyse", use_container_width=True):
                            with st.spinner("Analysiere Projektrisiken..."):
                                risk_prompt = f"""Analysiere die Risiken für folgendes Projekt:

{context}

Identifiziere:
1. TOP 3 RISIKEN (mit Eintrittswahrscheinlichkeit und Impact)
2. FR‹HINDIKATOREN für Probleme
3. GEGENSTEUERUNGSMASSNAHMEN

Sei konkret und praxisorientiert."""
                                risk_analysis = call_llama(risk_prompt)
                                st.markdown(risk_analysis)

                    with col_ana2:
                        if st.button("  Optimierungspotenziale", use_container_width=True):
                            with st.spinner("Suche Optimierungspotenziale..."):
                                opt_prompt = f"""Identifiziere Optimierungspotenziale für folgendes Projekt:

{context}

Finde:
1. EFFIZIENZSTEIGERUNGEN (Zeit & Kosten)
2. PROZESSVERBESSERUNGEN
3. QUICK WINS (schnell umsetzbar)

Priorisiere nach Impact und Umsetzbarkeit."""
                                opt_analysis = call_llama(opt_prompt)
                                st.markdown(opt_analysis)

# =========================
# Portfolio-Gesamtanalyse
# =========================
st.divider()
st.header("  Portfolio-Gesamtanalyse mit KI")

col_portfolio1, col_portfolio2 = st.columns(2)

with col_portfolio1:
    if st.button("  Portfolio-Gesundheitscheck", type="primary", use_container_width=True):
        with st.spinner("KI analysiert gesamtes Portfolio..."):
            portfolio_context = f"""PORTFOLIO-‹BERSICHT:
Anzahl Projekte: {len(filtered_projects)}
Gesamter Plan-Aufwand: {total_plan:.0f} Stunden
Gesamter Ist-Aufwand: {total_actual:.0f} Stunden
Durchschnittlicher Fortschritt: {avg_progress:.1f}%

STATUSVERTEILUNG:
{dict(status_counter)}

KRITISCHE PROJEKTE:
{len(critical_projects)} von {len(filtered_projects)} als kritisch eingestuft

TOP 3 KRITISCHSTE PROJEKTE:
{chr(10).join([f"- {p['name']}: Score {p['criticality']['score']}" for p in sorted(critical_projects, key=lambda x: x['criticality']['score'], reverse=True)[:3]]) if critical_projects else 'Keine kritischen Projekte'}"""

            portfolio_prompt = f"""Du bist ein Senior Portfolio-Manager. Analysiere die Portfolio-Gesundheit:

{portfolio_context}

Erstelle einen Executive Summary mit:
1. GESAMTBEWERTUNG (Ampel + 2-3 Sätze)
2. TOP 3 PORTFOLIO-RISIKEN
3. RESSOURCEN-ASSESSMENT
4. HANDLUNGSBEDARF (Priorisiert)
5. STRATEGISCHE EMPFEHLUNGEN

Sei strategisch und C-Level-orientiert."""

            portfolio_analysis = call_llama(portfolio_prompt)
            st.markdown(portfolio_analysis)

with col_portfolio2:
    if st.button("  Trend-Prognose", type="secondary", use_container_width=True):
        with st.spinner("KI erstellt Trend-Prognose..."):
            # Berechne zusätzliche Metriken für Prognose
            projects_over_budget = len([p for p in filtered_projects if p["variance"] > 0])
            avg_variance_pct = (total_actual - total_plan) / total_plan * 100 if total_plan > 0 else 0

            trend_context = f"""AKTUELLE TRENDS:
Durchschnittliche Abweichung: {avg_variance_pct:.1f}%
Projekte mit Budgetüberschreitung: {projects_over_budget} von {len(filtered_projects)}
Durchschnittlicher Fortschritt: {avg_progress:.1f}%

AMPEL-VERTEILUNG:
{dict(Counter(p['ampel'] for p in filtered_projects))}"""

            trend_prompt = f"""Als Trend-Analyst, prognostiziere die Portfolio-Entwicklung:

{trend_context}

Analysiere:
1. KURZFRIST-PROGNOSE (nächste 4 Wochen)
2. MITTELFRIST-TRENDS (nächste 3 Monate)
3. KRITISCHE WENDEPUNKTE
4. EMPFOHLENE STEUERUNGSMASSNAHMEN

Nutze Daten-Evidenz für Prognosen."""

            trend_analysis = call_llama(trend_prompt)
            st.markdown(trend_analysis)

# =========================
# Projekt-Vergleichsanalyse
# =========================
st.divider()
st.header("  Projekt-Vergleichsanalyse")

if len(filtered_projects) >= 2:
    col_comp1, col_comp2 = st.columns(2)

    with col_comp1:
        project_keys = [p["key"] for p in filtered_projects]
        compare_proj1 = st.selectbox("Projekt 1", options=project_keys, key="comp1")

    with col_comp2:
        compare_proj2 = st.selectbox("Projekt 2", options=project_keys, key="comp2")

    if st.button("  Projekte vergleichen", use_container_width=True):
        proj1 = next(p for p in filtered_projects if p["key"] == compare_proj1)
        proj2 = next(p for p in filtered_projects if p["key"] == compare_proj2)

        # Vergleichstabelle
        comparison_data = {
            "Metrik": ["Plan-Aufwand", "Ist-Aufwand", "Abweichung", "Fortschritt", "Ampel", "Kritikalität"],
            proj1["name"]: [
                f"{proj1['plan']:.0f}h",
                f"{proj1['actual']:.0f}h",
                f"{proj1['variance']:+.0f}h",
                f"{proj1['progress']:.1f}%",
                proj1['ampel'],
                proj1['criticality']['score']
            ],
            proj2["name"]: [
                f"{proj2['plan']:.0f}h",
                f"{proj2['actual']:.0f}h",
                f"{proj2['variance']:+.0f}h",
                f"{proj2['progress']:.1f}%",
                proj2['ampel'],
                proj2['criticality']['score']
            ]
        }

        comp_df = pd.DataFrame(comparison_data)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        # KI-Vergleichsanalyse
        if st.button("  KI-Vergleichsanalyse", type="primary"):
            with st.spinner("KI vergleicht Projekte..."):
                compare_context = f"""PROJEKT 1: {proj1['name']}
- Aufwand Plan/Ist: {proj1['plan']:.0f}h / {proj1['actual']:.0f}h
- Fortschritt: {proj1['progress']:.1f}%
- Ampel: {proj1['ampel']}
- Kritikalität: {proj1['criticality']['score']}

PROJEKT 2: {proj2['name']}
- Aufwand Plan/Ist: {proj2['plan']:.0f}h / {proj2['actual']:.0f}h
- Fortschritt: {proj2['progress']:.1f}%
- Ampel: {proj2['ampel']}
- Kritikalität: {proj2['criticality']['score']}"""

                compare_prompt = f"""Vergleiche diese beiden Projekte objektiv:

{compare_context}

Analysiere:
1. HAUPTUNTERSCHIEDE
2. STƒRKEN/SCHWƒCHEN BEIDER PROJEKTE
3. LESSONS LEARNED (Was kann ein Projekt vom anderen lernen?)
4. EMPFEHLUNGEN für beide Projekte

Sei fair und konstruktiv."""

                compare_analysis = call_llama(compare_prompt)
                st.markdown(compare_analysis)
else:
    st.info("Mindestens 2 Projekte erforderlich für Vergleichsanalyse")

# =========================
# Export & Reporting
# =========================
st.divider()
st.header("  Export & Reporting")

col_export1, col_export2, col_export3 = st.columns(3)

with col_export1:
    if st.button("  Excel-Export", use_container_width=True):
        export_data = []
        for p in filtered_projects:
            export_data.append({
                "Projektname": p["name"],
                "Nummer": p["number"],
                "Status": p["status"],
                "Ampel": p["ampel"],
                "Plan (h)": p["plan"],
                "Ist (h)": p["actual"],
                "Abweichung (h)": p["variance"],
                "Fortschritt (%)": round(p["progress"], 2),
                "Kritikalität": p["criticality"]["score"],
                "Kritisch": "Ja" if p["criticality"]["is_critical"] else "Nein"
            })

        export_df = pd.DataFrame(export_data)

        # Konvertiere zu Excel im Speicher
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Projekte')

        st.download_button(
            label="  Excel herunterladen",
            data=output.getvalue(),
            file_name=f"blue_ant_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

with col_export2:
    if st.button("  CSV-Export", use_container_width=True):
        export_data = []
        for p in filtered_projects:
            export_data.append({
                "Projektname": p["name"],
                "Nummer": p["number"],
                "Status": p["status"],
                "Ampel": p["ampel"],
                "Plan (h)": p["plan"],
                "Ist (h)": p["actual"],
                "Abweichung (h)": p["variance"],
                "Fortschritt (%)": round(p["progress"], 2),
                "Kritikalität": p["criticality"]["score"]
            })

        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False)

        st.download_button(
            label="  CSV herunterladen",
            data=csv,
            file_name=f"blue_ant_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

with col_export3:
    if st.button("  JSON-Export", use_container_width=True):
        export_data = []
        for p in filtered_projects:
            export_data.append({
                "name": p["name"],
                "number": p["number"],
                "status": p["status"],
                "ampel": p["ampel"],
                "plan": p["plan"],
                "actual": p["actual"],
                "variance": p["variance"],
                "progress": p["progress"],
                "criticality": p["criticality"]
            })

        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)

        st.download_button(
            label="  JSON herunterladen",
            data=json_str,
            file_name=f"blue_ant_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# =========================
# Footer
# =========================
st.divider()
st.caption("  Blue Ant Projekt-Controlling Dashboard | Powered by Streamlit & Llama 3")
st.caption(f"  Letzte Aktualisierung: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

