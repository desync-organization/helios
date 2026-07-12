from helios.workspace.repository_tasks import _homepage_files


def test_homepage_strategy_returns_real_source_files(tmp_path):
    page = tmp_path / "src" / "app" / "page.tsx"
    store = tmp_path / "src" / "lib" / "orchestrator-store.ts"
    page.parent.mkdir(parents=True)
    store.parent.mkdir(parents=True)
    page.write_text(
        'import { SettingsDialog } from "@/components/settings-dialog";\n'
        "export default function Home() {\n"
        "  const [settingsOpen] = useState(false);\n"
        "  const [, setActiveView] = useState(\"canvas\");\n"
        "  return (<>\n"
        "      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />\n"
        "  </>);\n"
        "}\n",
        encoding="utf-8",
    )
    store.write_text("export const useOrchestratorStore = () => null;\n", encoding="utf-8")

    files = _homepage_files(tmp_path, "Improve the homepage and expose runtime health")

    assert [record["path"] for record in files] == [
        "src/app/page.tsx",
        "src/components/runtime-status-bar.tsx",
    ]
    assert "RuntimeStatusBar" in files[0]["content"]
    assert "Helios is live" in files[1]["content"]


def test_homepage_strategy_refuses_unrelated_tasks(tmp_path):
    try:
        _homepage_files(tmp_path, "Update the database schema")
    except ValueError as error:
        assert "no repository-aware implementation strategy" in str(error)
    else:
        raise AssertionError("unrelated task must not produce a fabricated patch")
