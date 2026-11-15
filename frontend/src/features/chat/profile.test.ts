import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isUserProfile } from '../personal-state/profile.ts';

test('saved profiles retain farmer provenance and validate boundary coordinates', () => {
  const profile = { facts: { name: 'Alice', irrigation: 'Rainfed' }, boundary: { type: 'Polygon', coordinates: [[[32, 46], [33, 46], [33, 47], [32, 47], [32, 46]]] }, updated_at: 123, provenance: 'farmer_reported', verified: false };
  assert.equal(isUserProfile(profile), true);
  assert.equal(isUserProfile({ ...profile, boundary: null }), true);
  for (const patch of [{ facts: [] }, { facts: { name: 123 } }, { boundary: { type: 'Polygon', coordinates: ['bad'] } }, { updated_at: NaN }, { verified: true }]) assert.equal(isUserProfile({ ...profile, ...patch }), false);
});
