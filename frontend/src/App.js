import { useEffect, useState } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

function App() {
  const [query, setQuery] = useState("");
  const [apps, setApps] = useState([]);
  const [platform, setPlatform] = useState("");
  const [status, setStatus] = useState("Loading installed apps...");
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);

  useEffect(() => {
    loadApps();
  }, []);

  async function loadApps(searchText = "") {
    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/apps${searchText ? `?q=${encodeURIComponent(searchText)}` : ""}`
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not read installed apps.");
      }

      setApps(data.apps || []);
      setPlatform(data.platform || "");
      setStatus(
        data.count
          ? `Found ${data.count} apps on this ${data.platform} system.`
          : `No matching apps found on this ${data.platform} system.`
      );
    } catch (error) {
      setStatus(error.message || "Could not connect to the Python backend.");
      setApps([]);
    } finally {
      setLoading(false);
    }
  }

  async function launchByName(name) {
    if (!name.trim()) {
      setStatus("Type an app name first.");
      return;
    }

    setLaunching(true);
    setStatus(`Trying to open "${name}"...`);

    try {
      const response = await fetch(`${API_URL}/launch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "App launch failed.");
      }

      setStatus(data.message || `Opened "${name}".`);
      setQuery(data.app?.name || name);
      loadApps(name);
    } catch (error) {
      setStatus(error.message || "App launch failed.");
    } finally {
      setLaunching(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    launchByName(query);
  }

  async function handleSearchChange(event) {
    const nextValue = event.target.value;
    setQuery(nextValue);
    await loadApps(nextValue);
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div className="hero-copy">
          <span className="eyebrow">React + Python Desktop Launcher</span>
          <h1>Type an app name and press Enter.</h1>
          <p>
            The React UI talks to a local Python service that reads installed
            apps from your current computer and launches the best match.
          </p>
        </div>

        <form className="launch-form" onSubmit={handleSubmit}>
          <label className="label" htmlFor="app-name">
            App name
          </label>
          <div className="input-row">
            <input
              id="app-name"
              type="text"
              value={query}
              onChange={handleSearchChange}
              placeholder="Try Chrome, Calculator, VS Code, Terminal..."
              autoComplete="off"
            />
            <button type="submit" disabled={launching || loading}>
              {launching ? "Opening..." : "Open App"}
            </button>
          </div>
        </form>

        <div className="status-strip">
          <span className="status-label">Status</span>
          <p>{status}</p>
        </div>
      </section>

      <section className="results-card">
        <div className="results-header">
          <div>
            <span className="eyebrow">Installed Apps</span>
            <h2>{platform ? `${platform} launcher list` : "Launcher list"}</h2>
          </div>
          <span className="count-badge">{apps.length} shown</span>
        </div>

        {loading ? (
          <p className="empty-state">Scanning the system for launchable apps...</p>
        ) : apps.length === 0 ? (
          <p className="empty-state">
            No apps matched your search. Try a shorter name.
          </p>
        ) : (
          <div className="app-grid">
            {apps.map((appInfo) => (
              <button
                type="button"
                key={`${appInfo.name}-${appInfo.source}`}
                className="app-tile"
                onClick={() => launchByName(appInfo.name)}
              >
                <strong>{appInfo.name}</strong>
                <span>{appInfo.source}</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

export default App;

