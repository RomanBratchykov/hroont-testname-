export interface Location { latitude: number; longitude: number }
export interface ClimateMonth { period: string; days: number; values: Record<string, number | null>; coverage: Record<string, number> }
export interface ClimateData {
  status: 'available' | 'partial' | 'unavailable'; months: ClimateMonth[];
  units: Record<string, string>; source: string; source_url: string;
  retrieved_at: string | null; resolution: string; period: string;
  method: string; uncertainty_or_limitations: string; cached: boolean; reason?: string;
}
export interface DataSource {
  id: string; name: string; status: string; variables: string; resolution: string;
  limitation: string; source_url: string; checked_at: string;
  checks: { url: string; status: string; reason?: string; http_status?: number }[];
}
export interface NasaAccess { status: string; reason?: string; limitation: string; source_url: string; checked_at: string }
export function isNasaAccess(value: unknown): value is NasaAccess {
  return !!value && typeof value === 'object' && 'status' in value && typeof value.status === 'string'
    && 'limitation' in value && typeof value.limitation === 'string' && 'source_url' in value && typeof value.source_url === 'string'
    && 'checked_at' in value && typeof value.checked_at === 'string'
    && (!('reason' in value) || typeof value.reason === 'string');
}
export const PILOT: Location = { latitude: 46.7491, longitude: 32.7091 };
export function validLocation(value: unknown): value is Location {
  return !!value && typeof value === 'object' && 'latitude' in value && 'longitude' in value
    && typeof value.latitude === 'number' && typeof value.longitude === 'number'
    && Number.isFinite(value.latitude) && Number.isFinite(value.longitude)
    && Math.abs(value.latitude) <= 85 && Math.abs(value.longitude) <= 180;
}
export function project(location: Location, zoom: number) {
  const size = 256 * 2 ** zoom;
  const sin = Math.sin(location.latitude * Math.PI / 180);
  return { x: (location.longitude + 180) / 360 * size, y: (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * size };
}
export function unproject(x: number, y: number, zoom: number): Location {
  const size = 256 * 2 ** zoom;
  return { longitude: ((x / size * 360) % 360 + 360) % 360 - 180,
    latitude: Math.max(-85, Math.min(85, Math.atan(Math.sinh(Math.PI * (1 - 2 * y / size))) * 180 / Math.PI)) };
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
const variables = ['T2M', 'T2M_MAX', 'T2M_MIN', 'PRECTOTCORR', 'RH2M', 'WS2M', 'ALLSKY_SFC_SW_DWN'];
export function isClimateData(data: unknown): data is ClimateData {
  if (!record(data) || !['available', 'partial', 'unavailable'].includes(String(data.status)) || !Array.isArray(data.months) || data.months.length > 120 || !record(data.units)) return false;
  if (!['source', 'source_url', 'resolution', 'period', 'method', 'uncertainty_or_limitations'].every(key => typeof data[key] === 'string') || typeof data.cached !== 'boolean' || !(data.retrieved_at === null || typeof data.retrieved_at === 'string')) return false;
  if (data.status === 'unavailable') return data.months.length === 0 && typeof data.reason === 'string';
  const units = data.units;
  if (!variables.every(v => typeof units[v] === 'string')) return false;
  return data.months.length === 120 && data.months.every(month => {
    if (!record(month) || typeof month.period !== 'string' || !/^20(1[6-9]|2[0-5])-(0[1-9]|1[0-2])$/.test(month.period) || typeof month.days !== 'number' || !Number.isInteger(month.days) || month.days < 28 || month.days > 31 || !record(month.values) || !record(month.coverage)) return false;
    const values = month.values, coverage = month.coverage, days = month.days;
    return variables.every(v => (values[v] === null || (typeof values[v] === 'number' && Number.isFinite(values[v]))) && typeof coverage[v] === 'number' && Number.isInteger(coverage[v]) && coverage[v] >= 0 && coverage[v] <= days);
  });
}
export function isSourceResponse(data: unknown): data is { sources: DataSource[] } {
  if (!record(data) || !Array.isArray(data.sources) || data.sources.length !== 6) return false;
  return data.sources.every(source => record(source)
    && ['id', 'name', 'status', 'variables', 'resolution', 'limitation', 'source_url', 'checked_at'].every(key => typeof source[key] === 'string')
    && Array.isArray(source.checks) && source.checks.every(check => record(check) && typeof check.url === 'string' && typeof check.status === 'string'));
}
