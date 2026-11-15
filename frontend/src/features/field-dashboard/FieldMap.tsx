import { useRef, useState } from 'react';
import { project, unproject, type Location } from './types';

export function FieldMap({ selected, current, center, onCenter, onSelect }: {
  selected: Location; current: Location | null; center: Location;
  onCenter: (point: Location) => void; onSelect: (point: Location) => void;
}) {
  const [zoom, setZoom] = useState(11);
  const [tileError, setTileError] = useState(false);
  const pointer = useRef<{ x: number; y: number } | null>(null);
  const origin = project(center, zoom);
  const left = origin.x - 400, top = origin.y - 210;
  const count = 2 ** zoom;
  const tiles = [];
  for (let x = Math.floor(left / 256); x <= Math.floor((left + 800) / 256); x++) {
    for (let y = Math.floor(top / 256); y <= Math.floor((top + 420) / 256); y++) {
      if (y >= 0 && y < count) tiles.push(<image key={`${zoom}-${x}-${y}`} x={x * 256 - left} y={y * 256 - top} width="256" height="256" href={`https://tile.openstreetmap.org/${zoom}/${((x % count) + count) % count}/${y}.png`} onError={() => setTileError(true)} />);
    }
  }
  const marker = (point: Location, color: string, label: string) => {
    const world = project(point, zoom);
    const size = 256 * count;
    const dx = ((world.x - origin.x + size / 2) % size + size) % size - size / 2;
    return <g transform={`translate(${dx + 400},${world.y - top})`}><title>{label}</title><circle r="18" fill={color} opacity="0.18" /><circle r="8" fill={color} stroke="white" strokeWidth="3" /></g>;
  };
  return <div className="field-map">
    <svg viewBox="0 0 800 420" role="img" aria-label="Field location map. Click to select a point or drag to pan. Coordinates can also be entered below."
      onPointerDown={event => { pointer.current = { x: event.clientX, y: event.clientY }; event.currentTarget.setPointerCapture(event.pointerId); }}
      onPointerCancel={() => { pointer.current = null; }}
      onPointerUp={event => {
        if (!pointer.current) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        const dx = (event.clientX - pointer.current.x) * 800 / bounds.width;
        const dy = (event.clientY - pointer.current.y) * 420 / bounds.height;
        if (Math.abs(dx) + Math.abs(dy) > 6) onCenter(unproject(origin.x - dx, origin.y - dy, zoom));
        else onSelect(unproject(left + (event.clientX - bounds.left) * 800 / bounds.width, top + (event.clientY - bounds.top) * 420 / bounds.height, zoom));
        pointer.current = null;
      }}>
      <rect width="800" height="420" fill="#dce5d4" />{tiles}
      {current && marker(current, '#2774ec', 'Your browser location')}
      {marker(selected, '#c45c23', 'Selected field point — boundary not verified')}
    </svg>
    <div className="map-toolbar"><button aria-label="Zoom in" disabled={zoom >= 17} onClick={() => setZoom(z => z + 1)}>+</button><button aria-label="Zoom out" disabled={zoom <= 2} onClick={() => setZoom(z => z - 1)}>−</button><button aria-label="Center map on selected field" onClick={() => onCenter(selected)}>⌖</button></div>
    <div className="map-legend"><span><i className="field-dot" />Selected field</span><span><i className="location-dot" />Your location</span></div>
    {tileError && <p className="map-error" role="status">Some map tiles are unavailable. Coordinate selection still works.</p>}
    <a className="map-credit" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a>
  </div>;
}
