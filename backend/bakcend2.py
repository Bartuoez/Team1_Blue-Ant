from dotenv import load_dotenv
import os
import requests
import json
import pandas as pd
from typing import Optional, Dict, List

load_dotenv()


class BlueAntAPI:
    def __init__(self, api_key: str):
        self.base_url = "https://dashboard-examples.blueant.cloud/rest/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }

    # =========================================================
    # BASIC PROJECT / INVOICE
    # =========================================================

    def get_projects(self) -> Optional[Dict]:
        try:
            r = requests.get(f"{self.base_url}/projects", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"❌ Projects Fehler: {e}")
            return None

    def get_project_details(self, project_id: str) -> Optional[Dict]:
        try:
            r = requests.get(f"{self.base_url}/projects/{project_id}", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json().get("project")
        except requests.RequestException as e:
            print(f"❌ Project {project_id} Fehler: {e}")
            return None

    def get_project_invoices(self, project_id: str) -> List[Dict]:
        try:
            r = requests.get(f"{self.base_url}/projects/{project_id}/invoices", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json().get("invoices", [])
        except requests.RequestException as e:
            print(f"❌ Invoices Projekt {project_id}: {e}")
            return []

    def get_invoice_details(self, invoice_id: str) -> Optional[Dict]:
        try:
            r = requests.get(f"{self.base_url}/invoices/{invoice_id}", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json().get("invoice")
        except requests.RequestException as e:
            print(f"❌ Invoice {invoice_id}: {e}")
            return None

    # =========================================================
    # EXTENDED PROJECT DATA
    # =========================================================

    def get_project_kpis(self, project_id: str) -> List[Dict]:
        try:
            r = requests.get(f"{self.base_url}/projects/{project_id}/kpis", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json().get("kpis", [])
        except requests.RequestException:
            return []

    def get_planning_entries(self, project_id: str) -> List[Dict]:
        try:
            r = requests.get(f"{self.base_url}/projects/{project_id}/planningentries", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json().get("planningEntries", [])
        except requests.RequestException:
            return []

    def get_project_resources(self, project_id: str) -> List[Dict]:
        try:
            r = requests.get(f"{self.base_url}/projects/{project_id}/resources", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json().get("resources", [])
        except requests.RequestException:
            return []

    def get_project_roles(self, project_id: str) -> List[Dict]:
        try:
            r = requests.get(f"{self.base_url}/projects/{project_id}/roles", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json().get("roles", [])
        except requests.RequestException:
            return []

    def get_project_status_history(self, project_id: str) -> List[Dict]:
        try:
            r = requests.get(f"{self.base_url}/projects/{project_id}/statushistory", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json().get("statusHistory", [])
        except requests.RequestException:
            return []

    # =========================================================
    # EXPORT → CSV
    # =========================================================

    def export_all_to_csv(self, filename: str = "blueant_full_export.csv"):
        rows = []

        data = self.get_projects()
        if not data:
            print("❌ Keine Projekte gefunden")
            return

        for p in data.get("projects", []):
            project_id = p.get("id")
            if not project_id:
                continue

            print(f"📦 Projekt {project_id}")

            project = self.get_project_details(project_id)
            if not project:
                continue

            invoices = self.get_project_invoices(project_id)

            kpis = self.get_project_kpis(project_id)
            planning = self.get_planning_entries(project_id)
            resources = self.get_project_resources(project_id)
            roles = self.get_project_roles(project_id)
            status_history = self.get_project_status_history(project_id)

            if not invoices:
                rows.append({
                    "project_id": project_id,
                    "project_name": project.get("name"),
                    "project_number": project.get("number"),
                    "project_start": project.get("start"),
                    "project_end": project.get("end"),
                    "project_status_id": project.get("statusId"),

                    "invoice_id": None,
                    "invoice_number": None,
                    "invoice_amount": None,

                    "project_kpis": json.dumps(kpis, ensure_ascii=False),
                    "project_planning_entries": json.dumps(planning, ensure_ascii=False),
                    "project_resources": json.dumps(resources, ensure_ascii=False),
                    "project_roles": json.dumps(roles, ensure_ascii=False),
                    "project_status_history": json.dumps(status_history, ensure_ascii=False)
                })
                continue

            for inv in invoices:
                invoice_id = inv.get("id")
                invoice = self.get_invoice_details(invoice_id) or {}

                rows.append({
                    # PROJECT
                    "project_id": project_id,
                    "project_name": project.get("name"),
                    "project_number": project.get("number"),
                    "project_cost_center": project.get("costCentreNumber"),
                    "project_start": project.get("start"),
                    "project_end": project.get("end"),
                    "project_status_id": project.get("statusId"),
                    "project_type_id": project.get("typeId"),
                    "project_priority_id": project.get("priorityId"),
                    "planning_type": project.get("planningType"),
                    "billing_type": project.get("billingType"),

                    # INVOICE
                    "invoice_id": invoice_id,
                    "invoice_number": invoice.get("number") or inv.get("number"),
                    "invoice_amount": invoice.get("amount") or inv.get("amount"),
                    "invoice_discount": invoice.get("discount"),
                    "invoice_vat": invoice.get("vat"),
                    "invoice_status_id": invoice.get("statusId"),
                    "invoice_date": invoice.get("date"),
                    "invoice_due_date": invoice.get("dueDate"),

                    # COMPLEX DATA
                    "project_kpis": json.dumps(kpis, ensure_ascii=False),
                    "project_planning_entries": json.dumps(planning, ensure_ascii=False),
                    "project_resources": json.dumps(resources, ensure_ascii=False),
                    "project_roles": json.dumps(roles, ensure_ascii=False),
                    "project_status_history": json.dumps(status_history, ensure_ascii=False),
                })

        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False, encoding="utf-8-sig", sep=";")

        print(f"\n✅ Export fertig: {filename}")
        print(f"📊 Zeilen: {len(df)} | Spalten: {len(df.columns)}")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("❌ API_KEY fehlt (.env)")
        exit(1)

    api = BlueAntAPI(api_key)
    api.export_all_to_csv()
