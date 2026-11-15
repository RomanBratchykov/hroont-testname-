import { useEffect, useRef, useState } from 'react';
import { FieldMap } from './FieldMap';
import { BoundaryInput } from './BoundaryPreview';
import { ClimateChart } from './ClimateChart';
import { PILOT, validLocation, type ClimateData, type DataSource, type Location, isClimateData, isSourceResponse } from './types';
import './dashboard.css';

const SOURCE_NAMES = ['NASA POWER Daily', 'ISRIC SoilGrids WCS', 'NASADEM', 'NASA HLS S30 / L30', 'GPM IMERG Final V07', 'FAOSTAT'];
const STATUS_LABELS: Record<string, string> = { available: 'Data available', partial: 'Partial', unavailable: 'Unavailable', reachable: 'API responds', metadata_only: 'Metadata only', catalog_only: 'Catalog only', no_coverage: 'No matching data', authentication_required: 'Authentication required' };
function initialLocation(): Location {
  try { const value: unknown = JSON.parse(localStorage.getItem('croptato-field-point') ?? 'null'); return validLocation(value) ? value : PILOT; } catch { return PILOT; }
}
async function request(url: string, signal: AbortSignal): Promise<unknown> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`Data service returned ${response.status}. Please retry.`);
  const data: unknown = await response.json();
  if (!data || typeof data !== 'object') throw new Error('The data service returned an invalid response.');
  return data;
}
export function FieldDashboard({ onAsk }: { onAsk: (question: string) => void }) {
  const [selected, setSelected] = useState(initialLocation);
  const [center, setCenter] = useState(selected);
  const [current, setCurrent] = useState<Location | null>(null);
  const [climate, setClimate] = useState<ClimateData | null>(null);
  const [sources, setSources] = useState<DataSource[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState('');
  const [sourceError, setSourceError] = useState('');
  const [locationMessage, setLocationMessage] = useState('');
  const [locating, setLocating] = useState(false);
  const climateRequest = useRef<AbortController | null>(null);
  const sourcesRequest = useRef<AbortController | null>(null);
  const locationGeneration = useRef(0);
  useEffect(() => () => { climateRequest.current?.abort(); sourcesRequest.current?.abort(); locationGeneration.current++; }, []);
  const select = (point: Location) => {
    climateRequest.current?.abort(); sourcesRequest.current?.abort();
    climateRequest.current = null; sourcesRequest.current = null;
    setSelected(point); setCenter(point); setClimate(null); setSources(null); setError(''); setSourceError(''); setLoading(false); setChecking(false);
    try { localStorage.setItem('croptato-field-point', JSON.stringify(point)); } catch { /* Selection still works without storage. */ }
  };
  const query = `latitude=${selected.latitude.toFixed(4)}&longitude=${selected.longitude.toFixed(4)}`;
  const loadClimate = async () => {
    climateRequest.current?.abort();
    const controller = new AbortController(); climateRequest.current = controller;
    const timeout = window.setTimeout(() => controller.abort(new Error('NASA request timed out. Please retry.')), 75000);
    setLoading(true); setClimate(null); setError('');
    try {
      const data = await request(`/api/field-data?${query}`, controller.signal);
      if (!isClimateData(data)) throw new Error('Invalid climate response. Please retry.');
      if (!controller.signal.aborted) setClimate(data);
    } catch (e) { if (climateRequest.current === controller) setError(e instanceof Error ? e.message : 'NASA data is unavailable.'); }
    finally { clearTimeout(timeout); if (climateRequest.current === controller) setLoading(false); }
  };
  const checkSources = async () => {
    sourcesRequest.current?.abort();
    const controller = new AbortController(); sourcesRequest.current = controller;
    const timeout = window.setTimeout(() => controller.abort(new Error('Source check timed out. Please retry.')), 110000);
    setChecking(true); setSourceError('');
    try {
      const data = await request(`/api/data-sources?${query}`, controller.signal);
      if (!isSourceResponse(data)) throw new Error('Invalid source response.');
      if (!controller.signal.aborted) setSources(data.sources);
    } catch (e) { if (sourcesRequest.current === controller) setSourceError(e instanceof Error ? e.message : 'Could not check sources.'); }
    finally { clearTimeout(timeout); if (sourcesRequest.current === controller) setChecking(false); }
  };
  const locate = () => {
    if (!navigator.geolocation) { setLocationMessage('Geolocation is unavailable in this browser. Enter coordinates instead.'); return; }
    setLocating(true); setLocationMessage('Waiting for your browser location permission…');
    const generation = ++locationGeneration.current;
    navigator.geolocation.getCurrentPosition(position => {
      if (generation !== locationGeneration.current) return;
      const point = { latitude: position.coords.latitude, longitude: position.coords.longitude };
      setLocating(false);
      if (!validLocation(point)) { setLocationMessage('This location is outside the supported map range (85°S–85°N).'); return; }
      setCurrent(point); setCenter(point); setLocationMessage(`Blue dot: your location, accuracy approximately ${Math.round(position.coords.accuracy)} m. Click the map to choose a field.`);
    }, () => { if (generation === locationGeneration.current) { setLocating(false); setLocationMessage('Location was denied or unavailable. You can still click the map or enter coordinates.'); } }, { timeout: 15000, maximumAge: 60000, enableHighAccuracy: false });
  };
  const pilot = Math.abs(selected.latitude - PILOT.latitude) < .0001 && Math.abs(selected.longitude - PILOT.longitude) < .0001;
  const completeMonths = climate?.months.filter(m => Object.values(m.values).every(v => v !== null)).length;
  const download = () => {
    if (!climate) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify({ ...climate, api_checks: sources }, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = 'croptato-field-climate.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <div className="field-dashboard">
    <BoundaryInput />
    <section className="field-panel" aria-labelledby="field-map-heading">
      <div className="field-panel-heading"><div><p className="page-eyebrow">01 / Locate</p><h2 id="field-map-heading">Start with your field</h2><p className="field-note">Choose a point to explore its climate. A point is not a verified field boundary.</p></div><button className="quiet-button" onClick={locate} disabled={locating}>{locating ? 'Locating…' : '⌖ Locate me'}</button></div>
      <FieldMap selected={selected} current={current} center={center} onCenter={setCenter} onSelect={select} />
      <form className="coordinate-form" key={`${selected.latitude},${selected.longitude}`} onSubmit={event => {
        event.preventDefault(); const form = new FormData(event.currentTarget);
        const point = { latitude: Number(form.get('latitude')), longitude: Number(form.get('longitude')) };
        if (validLocation(point)) select(point);
      }}><label>Latitude<input name="latitude" aria-label="Field latitude" type="number" required min="-85" max="85" step="any" defaultValue={selected.latitude.toFixed(4)} /></label><label>Longitude<input name="longitude" aria-label="Field longitude" type="number" required min="-180" max="180" step="any" defaultValue={selected.longitude.toFixed(4)} /></label><button type="submit" className="field-button secondary">Set field</button><button type="button" className="quiet-button" onClick={() => select(PILOT)}>Kherson example ↗</button></form>
      <div className="field-selection"><span className="field-badge">{pilot ? 'Synthetic pilot location' : 'Selected point · boundary unverified'}</span><span>WGS84 · {selected.latitude.toFixed(4)}°, {selected.longitude.toFixed(4)}°</span></div>
      {locationMessage && <p role="status" className="field-note">{locationMessage}</p>}
      <p className="field-note">Selection is saved in this browser. Loading data sends the selected point to the listed providers. Map tiles come from OpenStreetMap.</p>
    </section>
    <div><button className="quiet-button" onClick={() => onAsk(`Retrieve NASA POWER historical climate for my selected point: latitude ${selected.latitude.toFixed(4)}, longitude ${selected.longitude.toFixed(4)}. Use 2025 initially and cite units, coverage and provenance. This is a selected point, not a verified field boundary; do not inherit the saved synthetic profile assumptions.`)}>Ask Soily about this location →</button></div>
    <div className="field-metrics"><div><span>Historical window</span><strong>2016–2025</strong><small>10 years · NASA POWER</small></div><div><span>Climate coverage</span><strong>{climate?.months.length ? `${completeMonths} / 120` : 'Not loaded'}</strong><small>Complete months across all 7 variables</small></div><div><span>API checks</span><strong>{sources ? `${sources.filter(s => !['unavailable', 'authentication_required'].includes(s.status)).length} / 6` : 'Not checked'}</strong><small>Responding sources · availability varies</small></div></div>
    <section className="field-panel" aria-labelledby="climate-heading">
      <div className="field-panel-heading"><div><p className="page-eyebrow">02 / Explore</p><h2 id="climate-heading">The climate behind your decisions</h2></div><button className="field-button" onClick={loadClimate} disabled={loading}>{loading ? 'Fetching NASA history…' : climate ? 'Refresh NASA data' : 'Load NASA history'}</button></div>
      {loading && <div className="field-empty" role="status"><span className="field-spinner" /><strong>Reading NASA POWER Daily</strong><p>Retrieving seven variables for 2016–2025 and checking daily coverage.</p></div>}
      {error && <p className="field-error" role="alert">{error}</p>}
      {!loading && !error && !climate && <div className="field-empty"><span className="empty-chart">▁ ▃ ▂ ▆ ▄ ▇ ▅</span><strong>A decade of climate, ready to explore</strong><p>Load historical temperature, rainfall, humidity, wind and sunlight for your selected point.</p><small>No simulated climate values are shown.</small></div>}
      {!loading && climate && (climate.status === 'unavailable' ? <p role="status" className="field-error">{climate.reason}</p> : <><div className="field-data-meta"><span className={`source-status ${climate.status}`}>{STATUS_LABELS[climate.status]}</span><span>NASA POWER · {climate.cached ? 'cached retrieval' : 'fresh retrieval'} · {climate.retrieved_at && new Date(climate.retrieved_at).toLocaleString()}</span></div><ClimateChart data={climate} /><details className="field-provenance"><summary>Where these numbers come from</summary><p>{climate.uncertainty_or_limitations}</p><p>{climate.resolution} · Method: {climate.method}</p><p>Climate belongs to the selected point. The saved example’s soil and crop assumptions remain separate.</p><a href={climate.source_url} target="_blank" rel="noreferrer">Open exact NASA request ↗</a><button className="quiet-button" onClick={download}>Download values & provenance ↓</button></details></>)}
    </section>
    <section className="field-panel" aria-labelledby="sources-heading"><div className="field-panel-heading"><div><p className="page-eyebrow">03 / Verify</p><h2 id="sources-heading">Every source, in the open</h2><p className="field-note">All six sources from the external API specification. Only retrieved NASA POWER values feed the charts.</p></div><button className="field-button secondary" onClick={checkSources} disabled={checking}>{checking ? 'Checking endpoints…' : 'Check API status'}</button></div>
      {checking && <p role="status" className="field-note">Testing providers from the server. Slow or restricted endpoints may take up to 90 seconds.</p>}{sourceError && <p className="field-error" role="alert">{sourceError}</p>}
      <div className="source-grid">{sources ? sources.map(source => <details className="source-card" key={source.id}><summary><span className="source-card-top"><span className="source-provider">{source.id === 'soilgrids' ? 'ISRIC' : source.id === 'faostat' ? 'FAO' : 'NASA'}</span><span className={`source-status ${source.status}`}>{STATUS_LABELS[source.status] ?? source.status}</span></span><strong>{source.name}</strong><span className="source-resolution">{source.resolution}</span><span className="source-expand">Inspect source & access details +</span></summary><p>{source.variables}</p><p>{source.limitation}</p><p>Checked {new Date(source.checked_at).toLocaleString()}. {source.id === 'power' ? 'One-day API probe; chart retrieval is separate.' : 'Not used in climate charts.'}</p><ul>{source.checks.map(check => <li key={check.url}><a href={check.url} target="_blank" rel="noreferrer">Exact request ↗</a> · {STATUS_LABELS[check.status] ?? check.status}</li>)}</ul></details>) : SOURCE_NAMES.map((name, i) => <div className="source-card unchecked" key={name}><div className="source-card-top"><span className="source-provider">{i === 1 ? 'ISRIC' : i === 5 ? 'FAO' : 'NASA'}</span><span className="source-status">Not checked</span></div><strong>{name}</strong><p>No live status has been measured yet.</p></div>)}</div>
      <p className="field-note">A successful metadata or catalog request does not mean raster values were downloaded or analyzed. FAO-56 and RUSLE are calculation methods, not data APIs. Erosion and profitability remain uncomputed.</p>
    </section>
  </div>;
}
