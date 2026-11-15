import { fieldBoundary } from '../field-dashboard/boundary.ts';

export interface UserProfile {
  facts: Record<string, string>;
  boundary: { type: 'Polygon'; coordinates: number[][][] } | null;
  updated_at: number | null;
  provenance: 'farmer_reported';
  verified: false;
}

export function isUserProfile(value: unknown): value is UserProfile {
  if (!value || typeof value !== 'object' || !('facts' in value) || !value.facts || typeof value.facts !== 'object' || Array.isArray(value.facts)) return false;
  if (!('boundary' in value)) return false;
  if (value.boundary !== null) {
    try { fieldBoundary(value.boundary); } catch { return false; }
  }
  return Object.values(value.facts).every(fact => typeof fact === 'string') && 'boundary' in value
    && (value.boundary === null || (typeof value.boundary === 'object' && 'type' in value.boundary && value.boundary.type === 'Polygon' && 'coordinates' in value.boundary && Array.isArray(value.boundary.coordinates)))
    && 'updated_at' in value && (value.updated_at === null || (typeof value.updated_at === 'number' && Number.isFinite(value.updated_at)))
    && 'verified' in value && value.verified === false && 'provenance' in value && value.provenance === 'farmer_reported';
}
