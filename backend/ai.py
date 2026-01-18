import pandas as pd
import subprocess


#DF für LLama vorbereiten
df = pd.read_csv("blueant_projects_invoices.csv", sep=";")

summary = {
    "rows": len(df),
    "columns": list(df.columns),
    "invoice_amount_sum": df["invoice_amount"].sum(),
    "invoice_amount_mean": df["invoice_amount"].mean(),
    "invoice_amount_max": df["invoice_amount"].max(),
    "projects_count": df["project_id"].nunique(),
}

sample_rows = df.sample(min(20, len(df))).to_dict(orient="records")




def ask_llama(prompt: str) -> str:
    result = subprocess.run(
        ["ollama", "run", "llama3"],
        input=prompt,
        text=True,
        capture_output=True
    )
    return result.stdout.strip()

#Propmt für LLama schreiben

prompt = f"""
Du bist ein erfahrener Projektcontroller.

DATENÜBERSICHT:
{json.dumps(summary, indent=2, ensure_ascii=False)}

BEISPIELDATEN:
{json.dumps(sample_rows, indent=2, ensure_ascii=False)}

AUFGABEN:
1. Erkenne auffällige Projekte (Kosten, Laufzeit, Rechnungen)
2. Identifiziere mögliche Risiken
3. Gib konkrete Handlungsempfehlungen
4. Antworte strukturiert in Stichpunkten
"""

#Ergebnis verarbeiten

with open("llama_analysis.txt", "w", encoding="utf-8") as f:
    f.write(analysis)



#KPIS bewerten 

risk_prompt = f"""
Bewerte jedes Projekt mit einem Risiko-Score von 1 (niedrig) bis 5 (hoch).
Nutze folgende Daten:

{json.dumps(sample_rows, ensure_ascii=False)}

Gib das Ergebnis als JSON zurück:
[
  {{ "project_id": "...", "risk_score": 3, "reason": "..." }}
]
"""

risk_json = ask_llama(risk_prompt)
print(risk_json)
