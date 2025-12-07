from dotenv import load_dotenv
import os
import requests
import json
from typing import Optional, Dict, List

load_dotenv()


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
                f"{self.base_url}/projects/778393700",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API-Fehler: {e}")
            return None

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

        # Optional: In Datei speichern
        # api.save_projects_to_file("blueant_projects.json")