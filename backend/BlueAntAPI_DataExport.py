import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
import time


class BlueAntAPI:
    # Hardcodierte Context Types
    CONTEXT_TYPES = [
        "Project",
        "Task",
        "Ticket",
        "Person",
        "Department",
        "Invoice",
        "Risk",
        "VoucherCollective",
        "Voucher",
        "Quote",
        "Proposal",
        "Todo",
        "Worktime",
        "StatusReport",
        "QuotePosition",
        "Portfolio",
        "Program",
        "Stakeholder",
        "ProjectResource",
        "Event"
    ]

    def __init__(self, api_key: str):
        self.base_url = "https://dashboard-examples.blueant.cloud/rest/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    # =========================
    # Basis GET
    # =========================
    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        url = f"{self.base_url}{endpoint}"

        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=10)
            # Zeige die tatsächliche finale URL an
            print(f"GET {r.url}")
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if e.response is not None:
                print(f"❌ {e.response.status_code} {e.response.text}")
            else:
                print(f"❌ Request Error: {e}")
            return None

    # =========================
    # PROJECTS
    # =========================
    def get_projects(self):
        res = self._get("/projects")
        return res.get("projects") if res else None

    def get_project(self, project_id: int):
        return self._get(f"/projects/{project_id}")

    def get_project_kpis(self, project_id: int):
        return self._get(f"/projects/{project_id}/kpis")

    def get_project_planningentries(self, project_id: int):
        """Holt alle Planning Entries mit Details"""
        return self._get(f"/projects/{project_id}/planningentries")

    # =========================
    # MASTERDATA
    # =========================
    def get_project_statuses(self):
        """Holt alle Projekt-Status"""
        return self._get("/masterdata/projects/statuses")

    def get_customfield_contexttypes(self):
        """Holt alle Custom Field Context Types"""
        return self._get("/masterdata/customfield/contexttypes")

    def get_customfield_definitions(self, context_type: str):
        """Holt Custom Field Definitionen für einen Context Type"""
        return self._get(
            f"/masterdata/customfield/definitions/{context_type}"
        )

    # =========================
    # FULL EXPORT PROJECTS
    # =========================
    def export_all_projects(self) -> Dict[int, Dict[str, Any]]:
        """Exportiert alle Projektdaten"""
        export = {}

        projects = self.get_projects()
        if not projects:
            print("❌ Keine Projekte gefunden")
            return export

        print(f"✅ {len(projects)} Projekte gefunden")

        for project in projects:
            project_id = project["id"]
            print(f"\n📦 Exportiere Projekt {project_id}")

            export[project_id] = {
                "project": self.get_project(project_id),
                "kpis": self.get_project_kpis(project_id),
                "planningentries": self.get_project_planningentries(project_id),
            }

            time.sleep(0.2)  # Rate-Limit-Schutz

        return export

    # =========================
    # FULL EXPORT MASTERDATA
    # =========================
    def export_all_masterdata(self) -> Dict[str, Any]:
        """Exportiert alle Masterdata"""
        export = {}

        print("\n" + "=" * 60)
        print("🔧 MASTERDATA EXPORT")
        print("=" * 60)

        # 1. Projekt-Status
        print("\n📊 Lade Projekt-Status...")
        statuses = self.get_project_statuses()
        if statuses:
            export["project_statuses"] = statuses
            status_count = len(statuses.get("projectStatus", []))
            print(f"✅ {status_count} Status geladen")
            time.sleep(0.2)

        # 2. Custom Field Context Types (nur zur Info speichern)
        print("\n📝 Lade Custom Field Context Types...")
        context_types_response = self.get_customfield_contexttypes()
        if context_types_response:
            export["customfield_contexttypes"] = context_types_response
            print(f"✅ Context Types geladen")

        # 3. Custom Field Definitions - mit hardcodierter Liste
        print(f"\n🔍 Lade Definitionen für {len(self.CONTEXT_TYPES)} Context Types...")
        definitions = {}

        for ctx_type in self.CONTEXT_TYPES:
            print(f"   → {ctx_type}")
            defs = self.get_customfield_definitions(ctx_type)
            if defs:
                definitions[ctx_type] = defs
                # Zähle Custom Fields falls vorhanden
                if "customFields" in defs:
                    print(f"      ✓ {len(defs['customFields'])} Custom Fields")
            time.sleep(0.15)  # Rate-Limit-Schutz

        if definitions:
            export["customfield_definitions"] = definitions
            print(f"\n✅ Definitionen für {len(definitions)} Context Types geladen")

        return export

    # =========================
    # KOMBINIEREN
    # =========================
    def combine_data(self, projects_data: Dict, masterdata: Dict) -> List[Dict[str, Any]]:
        """Kombiniert Project- und Masterdata über IDs"""
        combined = []

        # Status-Lookup erstellen (aus projectStatus Array)
        status_lookup = {}
        if "project_statuses" in masterdata:
            statuses = masterdata["project_statuses"].get("projectStatus", [])
            for status in statuses:
                status_id = status.get("id")
                if status_id:
                    status_lookup[status_id] = status

        for project_id, project_info in projects_data.items():
            project = project_info.get("project", {})

            # Basis-Projektdaten
            combined_entry = {
                "project_id": project_id,
                "project_data": project,
                "kpis": project_info.get("kpis"),
                "planningentries": project_info.get("planningentries"),
            }

            # Status-Info aus Masterdata hinzufügen
            status_id = project.get("statusID")
            if status_id and status_id in status_lookup:
                combined_entry["status_info"] = status_lookup[status_id]

            # Custom Fields Definitionen hinzufügen
            if "customfield_definitions" in masterdata:
                # Nur Project Context Type Definitionen hinzufügen
                project_customfields = masterdata["customfield_definitions"].get("Project")
                if project_customfields:
                    combined_entry["customfield_definitions"] = project_customfields

            combined.append(combined_entry)

        return combined


def save_json(data: Any, filename: str):
    """Speichert Daten als JSON-Datei"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Gespeichert: {filename}")


if __name__ == "__main__":
    api_key = "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiI4MzM2NzA5NjIiLCJpYXQiOjE3NjMxMzU2OTAsImlzcyI6IkJsdWUgQW50wqkiLCJleHAiOjE5MjA4MTU2OTB9.7wuTY1xVr5kWnT_5GFBN2rSI9IkcwaW2JKdvFRGn_rw"
    api = BlueAntAPI(api_key)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "=" * 60)
    print("🚀 BLUE ANT DATEN EXPORT")
    print("=" * 60)

    # 1. PROJECTS exportieren
    print("\n📦 EXPORTIERE PROJEKTE...")
    projects_data = api.export_all_projects()
    projects_filename = f"blueant_projects_{timestamp}.json"
    save_json(projects_data, projects_filename)
    print(f"✅ {len(projects_data)} Projekte exportiert")

    # 2. MASTERDATA exportieren
    print("\n🔧 EXPORTIERE MASTERDATA...")
    masterdata = api.export_all_masterdata()
    masterdata_filename = f"blueant_masterdata_{timestamp}.json"
    save_json(masterdata, masterdata_filename)
    print(f"✅ Masterdata exportiert")

    # 3. KOMBINIERTE DATEN erstellen
    print("\n🔗 KOMBINIERE DATEN...")
    combined_data = api.combine_data(projects_data, masterdata)
    combined_filename = f"blueant_combined_{timestamp}.json"
    save_json(combined_data, combined_filename)
    print(f"✅ {len(combined_data)} kombinierte Datensätze erstellt")

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("✨ EXPORT ABGESCHLOSSEN")
    print("=" * 60)
    print(f"📁 Erstellt:")
    print(f"   1. {projects_filename}")
    print(f"   2. {masterdata_filename}")
    print(f"   3. {combined_filename}")
    print("=" * 60)