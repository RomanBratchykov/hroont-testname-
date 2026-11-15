import { useEffect, useState } from 'react';
import { FieldMap } from './FieldMap';
import { boundaryView, fieldBoundary } from './boundary';
import type { Location } from './types';
import { command } from '../chat/api';
import { isUserProfile } from '../personal-state/profile';
import './dashboard.css';

export function BoundaryMap({ points }: { points: Location[] }) {
  const view = boundaryView(points);
  const [center, setCenter] = useState(view.center);
  return <div><FieldMap selected={view.center} current={null} center={center} onCenter={setCenter} onSelect={setCenter} boundary={points} initialZoom={view.zoom}/><p className="field-note">Farmer-provided boundary · WGS84 · Unverified</p></div>;
}

export function BoundaryPreview({ text }: { text: string }) {
  let points: Location[];
  try {
    const attached = text.match(/\[Untrusted attachment: [^\n]+\]\n([\s\S]*?)\n\[End attachment\]/);
    const clean = (attached?.[1] ?? text).trim().replace(/^```(?:json|geojson)?\s*/i, '').replace(/\s*```$/, '');
    points = fieldBoundary(JSON.parse(clean));
  } catch { return null; }
  return <BoundaryMap key={JSON.stringify(points)} points={points}/>;
}

export function BoundaryInput({ onField }: { onField?: (point: Location) => void } = {}) {
  const [text, setText] = useState('');
  const [points, setPoints] = useState<Location[] | null>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState('');
  const connected = import.meta.env.VITE_CHAT_BACKEND === 'on';
  useEffect(() => {
    if (!connected) return;
    const abort = new AbortController();
    void command({ action: 'profile' }, abort.signal).then(value => {
      if (!isUserProfile(value)) throw new Error('Could not read the saved field.');
      if (value.boundary && !abort.signal.aborted) {
        const loaded = fieldBoundary(value.boundary);
        setPoints(previous => previous ?? loaded);
        onField?.(boundaryView(loaded).center);
      }
    }).catch(reason => { if (!abort.signal.aborted) setError(reason instanceof Error ? reason.message : 'Could not load the saved field.'); });
    return () => abort.abort();
  }, [connected, onField]);
  const save = async () => {
    if (!points || saving) return;
    setSaving(true); setError(''); setSaved('');
    try {
      const value = await command({ action: 'save_profile', profile: { boundary: points.map(point => [point.longitude, point.latitude]) } });
      if (!isUserProfile(value) || !value.boundary) throw new Error('The server did not confirm saving the field.');
      setSaved('Field boundary saved to your profile.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save the field.'); }
    finally { setSaving(false); }
  };
  return <section className="field-panel"><h3>Show a field boundary</h3><form onSubmit={event => {
    event.preventDefault();
    try { const field = fieldBoundary(JSON.parse(text)); setPoints(field); onField?.(boundaryView(field).center); setError(''); setSaved(''); }
    catch (reason) { setError(reason instanceof SyntaxError ? 'Paste a JSON array of four [longitude, latitude] pairs or a GeoJSON Polygon.' : reason instanceof Error ? reason.message : 'Invalid boundary.'); }
  }}><label>Four corners in boundary order [longitude, latitude]<textarea aria-label="Field boundary coordinates" rows={5} value={text} onChange={event => setText(event.target.value)} placeholder="[[32.691944,46.733694],[32.686611,46.764778],[32.732806,46.766306],[32.730944,46.731722]]"/></label><button className="field-button secondary" type="submit" disabled={saving}>Show on map</button></form>{error && <p role="alert">{error}</p>}{points && <><BoundaryMap key={JSON.stringify(points)} points={points}/><button type="button" className="field-button secondary" disabled={!connected || saving} onClick={() => { void save(); }}>{saving ? 'Saving…' : 'Save field'}</button>{!connected && <p>Connect the backend to save this field.</p>}</>}{saved && <p role="status">{saved}</p>}</section>;
}
