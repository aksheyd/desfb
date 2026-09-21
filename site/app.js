(() => {
  const DATA = "data/public";

  async function loadJSON(name) {
    const res = await fetch(`${DATA}/${name}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`${name}: ${res.status}`);
    return res.json();
  }

  function fmtSynced(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return `Synced ${d.toLocaleString("en-US", {
        timeZone: "America/Los_Angeles",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZoneName: "short",
      })}`;
    } catch {
      return `Synced ${iso}`;
    }
  }

  function fmtTideTime(t) {
    // "2026-09-20 10:31" local LST/LDT from CO-OPS
    if (!t) return "—";
    const m = t.match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
    if (!m) return t;
    const hour = Number(m[4]);
    const ampm = hour >= 12 ? "PM" : "AM";
    const h12 = hour % 12 || 12;
    return `${h12}:${m[5]} ${ampm}`;
  }

  function renderTides(tides) {
    const ul = document.getElementById("tides-list");
    const preds = (tides && tides.predictions) || [];
    if (!preds.length) {
      ul.innerHTML = `<li class="err">${(tides && tides.error) || "No tide predictions available."}</li>`;
      return;
    }
    ul.innerHTML = preds
      .map(
        (p) => `<li>
          <span><span class="tide-type ${p.type}">${p.type}</span> · ${fmtTideTime(p.time)}</span>
          <span>${p.height_ft != null ? `${p.height_ft.toFixed(1)} ft` : "—"}</span>
        </li>`
      )
      .join("");
  }

  function renderForecast(forecast) {
    const place = document.getElementById("forecast-place");
    const box = document.getElementById("forecast-list");
    if (forecast && (forecast.city || forecast.state)) {
      place.textContent = `NWS · ${[forecast.city, forecast.state].filter(Boolean).join(", ")}`;
    }
    const periods = (forecast && forecast.periods) || [];
    if (!periods.length) {
      box.innerHTML = `<p class="err">${(forecast && forecast.error) || "Forecast unavailable."}</p>`;
      return;
    }
    box.innerHTML = periods
      .slice(0, 4)
      .map(
        (p) => `<div class="forecast-item">
          <strong>${p.name || "Period"}</strong>
          <span class="forecast-temp">${p.temperature}°${p.temperatureUnit || "F"}</span>
          · ${p.shortForecast || ""}
          ${p.windSpeed ? `<div class="sub">${p.windDirection || ""} ${p.windSpeed}</div>` : ""}
        </div>`
      )
      .join("");
  }

  function renderSeason(season) {
    document.getElementById("season-label").textContent = season.label
      ? `${season.label} spotlight`
      : "";
    document.getElementById("season-note").textContent = season.note || "";
    const ul = document.getElementById("season-list");
    const items = season.highlights || [];
    if (!items.length) {
      ul.innerHTML = "<li class='err'>No seasonal highlights yet.</li>";
      return;
    }
    const label = { a: "abundant", c: "common", u: "uncommon" };
    ul.innerHTML = items
      .map(
        (b) => `<li class="chip">
          <span>${b.common_name}</span>
          <small>${label[b.abundance] || b.abundance}${b.nests_locally ? " · nests locally" : ""}</small>
        </li>`
      )
      .join("");
  }

  function renderFeatured(featured) {
    const box = document.getElementById("featured-list");
    const species = (featured && featured.species) || [];
    box.innerHTML = species
      .map((s) => {
        const badges = [];
        if (s.federal) badges.push(`<span class="badge">Federal ${s.federal}</span>`);
        if (s.state) badges.push(`<span class="badge state">State ${s.state}</span>`);
        return `<article class="species-card">
          <h3>${s.common_name}</h3>
          <p class="sci">${s.scientific_name || ""}</p>
          <div class="badges">${badges.join("")}</div>
          <p>${s.blurb || ""}</p>
        </article>`;
      })
      .join("");
  }

  async function init() {
    try {
      const [today, season, featured] = await Promise.all([
        loadJSON("today.json"),
        loadJSON("season.json"),
        loadJSON("featured.json"),
      ]);
      document.getElementById("synced-at").textContent = fmtSynced(today.synced_at);
      renderTides(today.tides);
      renderForecast(today.forecast);
      renderSeason(season);
      renderFeatured(featured);
    } catch (err) {
      document.getElementById("synced-at").textContent = "Could not load live data.";
      document.getElementById("tides-list").innerHTML = `<li class="err">${err.message}</li>`;
      console.error(err);
    }
  }

  init();
})();
