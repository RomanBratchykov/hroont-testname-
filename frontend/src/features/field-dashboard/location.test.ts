import test from 'node:test';
import assert from 'node:assert/strict';
import { isNasaAccess, project, unproject, validLocation } from './types.ts';

test('map projection round trips field locations across zoom levels and hemispheres', () => {
  for (const point of [{ latitude: 46.7491, longitude: 32.7091 }, { latitude: -32, longitude: -170 }, { latitude: 84, longitude: 179.9 }]) {
    for (const zoom of [2, 11, 17]) {
      const world = project(point, zoom);
      const result = unproject(world.x, world.y, zoom);
      assert.ok(Math.abs(result.latitude - point.latitude) < 1e-9);
      assert.ok(Math.abs(result.longitude - point.longitude) < 1e-9);
    }
  }
});

test('coordinates reject corrupt saved selections and nonfinite values', () => {
  for (const point of [null, {}, { latitude: '46', longitude: 32 }, { latitude: NaN, longitude: 32 }, { latitude: 86, longitude: 32 }, { latitude: 40, longitude: 181 }]) assert.equal(validLocation(point), false);
  assert.equal(validLocation({ latitude: 0, longitude: 0 }), true);
});

test('NASA Open APIs connection information validates without requiring a secret in the browser', () => {
  assert.equal(isNasaAccess({ status: 'reachable', limitation: 'Connection check only.', source_url: 'https://api.nasa.gov', checked_at: '2026-11-15T00:00:00Z' }), true);
  assert.equal(isNasaAccess({ status: 'reachable' }), false);
  assert.equal(isNasaAccess({ status: 'reachable', limitation: 'Connection check only.', source_url: 'https://api.nasa.gov', checked_at: 'now', reason: 123 }), false);
});

test('dashboard rejects invalid server payloads instead of drawing invented zeros', async () => {
  const { isClimateData, isSourceResponse } = await import('./types.ts');
  assert.equal(isClimateData({ status: 'available', months: [], units: {} }), false);
  assert.equal(isClimateData({ status: 'unavailable', months: [], units: {}, source: 'NASA POWER Daily', source_url: 'https://power.larc.nasa.gov', resolution: 'grid', period: '2016–2025', method: 'monthly-complete-daily-v1', uncertainty_or_limitations: 'Regional estimates', cached: false, retrieved_at: null, reason: 'Timeout' }), true);
  assert.equal(isSourceResponse({ sources: [{ id: 'power', status: 'reachable' }] }), false);
});
