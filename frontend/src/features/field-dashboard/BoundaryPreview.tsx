import { useState } from 'react';
import { FieldMap } from './FieldMap';
import { boundaryView, fieldBoundary } from './boundary';
import type { Location } from './types';
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

export function BoundaryInput() {
  const [text, setText] = useState('');
  const [points, setPoints] = useState<Location[] | null>(null);
  const [error, setError] = useState('');
  return <section className="field-panel"><h3>Show a field boundary</h3><form onSubmit={event => {
    event.preventDefault();
    try { setPoints(fieldBoundary(JSON.parse(text))); setError(''); }
    catch (reason) { setError(reason instanceof SyntaxError ? 'Paste a JSON array of four [longitude, latitude] pairs or a GeoJSON Polygon.' : reason instanceof Error ? reason.message : 'Invalid boundary.'); }
  }}><label>Four corners in boundary order [longitude, latitude]<textarea aria-label="Field boundary coordinates" rows={5} value={text} onChange={event => setText(event.target.value)} placeholder="[[32.691944,46.733694],[32.686611,46.764778],[32.732806,46.766306],[32.730944,46.731722]]"/></label><button className="field-button secondary" type="submit">Show on map</button></form>{error && <p role="alert">{error}</p>}{points && <BoundaryMap key={JSON.stringify(points)} points={points}/>}</section>;
}
