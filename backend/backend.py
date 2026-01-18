from dotenv import load_dotenv
import os
import requests
import json
from typing import Optional, Dict, List

load_dotenv()

#Push
class BlueAntAPI:
    def __init__(self, api_key: str):
        self.base_url = "https://dashboard-examples.blueant.cloud/rest/v1"
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }

    def get_projects(self) -> Optional[Dict]:
        """Holt alle Projekte von der API"""
        try:
            response = requests.get(
                f"{self.base_url}/projects",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API-Fehler: {e}")
            return None

    def get_project_details(self, project_id: str) -> Optional[Dict]:
        """Holt Detaildaten zu einem Projekt per ID"""
        try:
            response = requests.get(
                f"{self.base_url}/projects/{project_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API-Fehler für Projekt {project_id}: {e}")
            return None

    def get_project_names_and_ids(self) -> List[Dict[str, str]]:
        """Gibt eine Liste von Dicts mit Projektnamen und IDs zurück"""
        data = self.get_projects()
        if not data:
            return []

        projects = data.get("projects", [])
        results: List[Dict[str, str]] = []

        for project in projects:
            pid = project.get("id")
            if not pid:
                continue

            details = self.get_project_details(pid)
            if not details:
                continue

            name = details.get("name") or details.get("project", {}).get("name")
            # Fallback: falls Name nicht vorhanden, nur ID speichern
            results.append({"id": pid, "name": name or "Unbekannt"})

        return results

    def get_project_kpis(self, project_id: str) -> List[Dict]:
        """Holt KPIs für ein einzelnes Projekt über /projects/{id}/kpis"""
        try:
            response = requests.get(
                f"{self.base_url}/projects/{project_id}/kpis",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("kpis", [])
        except requests.exceptions.RequestException as e:
            print(f"❌ API-Fehler (KPIs) für Projekt {project_id}: {e}")
            return []

    def plot_kpis_for_all_projects(self, save_dir: str = "plots"):
        """
        Holt alle Projekt-IDs, zieht deren KPIs und erstellt pro Projekt
        ein Balkendiagramm (KPI-Name vs. Wert). Nicht-numerische Werte
        werden übersprungen.
        """
        try:
            import matplotlib.pyplot as plt  # type: ignore
        except ImportError:
            print("❌ matplotlib nicht installiert. Bitte `pip install matplotlib` ausführen.")
            return

        os.makedirs(save_dir, exist_ok=True)
        projects = self.get_project_names_and_ids()
        if not projects:
            print("Keine Projekte gefunden.")
            return

        for project in projects:
            pid = project["id"]
            pname = project["name"]
            kpis = self.get_project_kpis(pid)
            if not kpis:
                print(f"⚠️ Keine KPIs für Projekt {pid} ({pname})")
                continue

            names = []
            values = []
            for kpi in kpis:
                name = kpi.get("name") or kpi.get("id")
                value = kpi.get("value")
                # Nur numerische Werte plotten
                if isinstance(value, (int, float)):
                    names.append(name)
                    values.append(value)

            if not values:
                print(f"⚠️ Keine numerischen KPI-Werte für Projekt {pid} ({pname})")
                continue

            plt.figure(figsize=(10, 5))
            plt.bar(names, values, color="#4C8BF5")
            plt.xticks(rotation=45, ha="right")
            plt.ylabel("KPI-Wert")
            plt.title(f"KPIs für Projekt {pname} (ID: {pid})")
            plt.tight_layout()

            outfile = os.path.join(save_dir, f"project_{pid}_kpis.png")
            plt.savefig(outfile)
            plt.close()
            print(f"✅ KPI-Plot gespeichert: {outfile}")

    def save_projects_to_file(self, filename: str = "projects.json"):
        """Speichert Projekte in eine JSON-Datei"""
        data = self.get_projects()
        if data:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Projekte gespeichert in: {filename}")
            return True
        return False

    def print_project_summary(self):
        """Gibt eine Zusammenfassung aller Projekte aus"""
        data = self.get_projects()

        if not data:
            print("Keine Daten erhalten.")
            return

        projects = data.get('projects', [])

        print(f"\n{'=' * 80}")
        print(f"📊 PROJEKT-ÜBERSICHT")
        print(f"{'=' * 80}\n")
        print(f"Status: {data.get('status')}")
        print(f"Timestamp: {data.get('timestamp')}")
        print(f"Anzahl Projekte: {len(projects)}\n")

        for idx, project in enumerate(projects, 1):
            print(f"Projekt #{idx}")
            print(f"  ├─ ID: {project.get('id')}")
            print(f"  ├─ Currency ID: {project.get('currencyId')}")
            print(f"  ├─ Department ID: {project.get('departmentId')}")
            print(f"  ├─ Type ID: {project.get('typeId')}")
            print(f"  ├─ Status ID: {project.get('statusId')}")
            print(f"  ├─ Program ID: {project.get('programId')}")
            print(f"  ├─ Priority ID: {project.get('priorityId')}")

            # Subdivisions
            subdivisions = project.get('subdivisions', [])
            print(f"  ├─ Subdivisions: {len(subdivisions)}")

            # Portfolio IDs
            portfolio_ids = project.get('portfolioIds', [])
            print(f"  ├─ Portfolios: {portfolio_ids}")

            # Clients
            clients = project.get('clients', [])
            print(f"  └─ Clients: {len(clients)}")

            if clients:
                for client in clients:
                    print(f"      ├─ Client ID: {client.get('clientId')}")
                    print(f"      └─ Share: {client.get('share')}%")

            print()


# ==================== VERWENDUNG ====================

if __name__ == "__main__":
    api_key = os.getenv("API_KEY")

    if not api_key:
        print("❌ API_KEY nicht in .env gefunden!")
    else:
        # API-Instanz erstellen
        api = BlueAntAPI(api_key)

        # Projekt-Zusammenfassung anzeigen
        api.print_project_summary()

        # Namen und IDs tabellarisch ausgeben
        table = api.get_project_names_and_ids()
        if table:
            print(f"\n{'=' * 80}")
            print(f"📋 Projektnamen und IDs")
            print(f"{'=' * 80}")
            for row in table:
                print(f"ID: {row['id']} | Name: {row['name']}")
        else:
            print("Keine Projektnamen/IDs abrufbar.")

        # Optional: In Datei speichern
        # api.save_projects_to_file("blueant_projects.json")

        #Optional: KPI-Plots erzeugen (PNG-Dateien in ./plots)
        api.plot_kpis_for_all_projects()