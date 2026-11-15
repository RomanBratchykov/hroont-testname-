import { project, unproject, validLocation, type Location } from './types.ts';

// WGS84 coordinate pairs follow GeoJSON order: [longitude, latitude].
export function fieldBoundary(input: unknown): Location[] {
  let value = input;
  if (value && typeof value === 'object' && 'type' in value && value.type === 'Feature' && 'geometry' in value) value = value.geometry;
  if (value && typeof value === 'object' && 'type' in value && value.type === 'Polygon' && 'coordinates' in value) {
    if (!Array.isArray(value.coordinates) || value.coordinates.length !== 1) throw new Error('Supply one field boundary without holes.');
    value = value.coordinates[0];
  }
  if (!Array.isArray(value)) throw new Error('Supply four [longitude, latitude] pairs or a GeoJSON Polygon.');
  const points = value.map((pair: unknown) => {
    if (!Array.isArray(pair) || pair.length !== 2) throw new Error('Each corner must be [longitude, latitude].');
    const point = { longitude: pair[0], latitude: pair[1] };
    if (!validLocation(point)) throw new Error('Use numeric WGS84 coordinates: longitude −180 to 180, latitude −85 to 85.');
    return point;
  });
  if (points.length === 5 && points[0].latitude === points[4].latitude && points[0].longitude === points[4].longitude) points.pop();
  if (points.length !== 4 || new Set(points.map(p => `${p.longitude},${p.latitude}`)).size !== 4) throw new Error('Supply exactly four distinct corners in boundary order.');
  if (Math.max(...points.map(p => p.longitude)) - Math.min(...points.map(p => p.longitude)) >= 180) throw new Error('Boundaries crossing the date line are not supported.');
  const cross = (a: Location, b: Location, c: Location) => (b.longitude - a.longitude) * (c.latitude - a.latitude) - (b.latitude - a.latitude) * (c.longitude - a.longitude);
  const intersects = (a: Location, b: Location, c: Location, d: Location) => cross(a, b, c) * cross(a, b, d) <= 0 && cross(c, d, a) * cross(c, d, b) <= 0;
  if (intersects(points[0], points[1], points[2], points[3]) || intersects(points[1], points[2], points[3], points[0]) || points.some((p, i) => cross(p, points[(i + 1) % 4], points[(i + 2) % 4]) === 0)) throw new Error('Corners must form a nonzero field boundary without crossing edges.');
  return points;
}

export function boundaryView(points: Location[]) {
  const projected = points.map(p => project(p, 0));
  const width = Math.max(...projected.map(p => p.x)) - Math.min(...projected.map(p => p.x));
  const height = Math.max(...projected.map(p => p.y)) - Math.min(...projected.map(p => p.y));
  return {
    center: unproject((Math.min(...projected.map(p => p.x)) + Math.max(...projected.map(p => p.x))) / 2, (Math.min(...projected.map(p => p.y)) + Math.max(...projected.map(p => p.y))) / 2, 0),
    zoom: Math.max(2, Math.min(17, Math.floor(Math.log2(Math.min(680 / width, 300 / height))))),
  };
}
