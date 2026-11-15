import test from 'node:test';
import assert from 'node:assert/strict';
import { fieldBoundary, boundaryView } from './boundary.ts';

const corners = [[32.691944, 46.733694], [32.686611, 46.764778], [32.732806, 46.766306], [32.730944, 46.731722]];
test('four corners and the supplied closed GeoJSON produce the same field', () => {
  const field = fieldBoundary(corners);
  assert.deepEqual(fieldBoundary({ type: 'Polygon', coordinates: [[...corners, corners[0]]] }), field);
  assert.deepEqual(fieldBoundary({ type: 'Feature', geometry: { type: 'Polygon', coordinates: [corners] } }), field);
  const view = boundaryView(field);
  assert.ok(view.zoom >= 11 && view.zoom <= 14);
  assert.ok(Math.abs(view.center.latitude - 46.749) < .01);
});
test('invalid, crossed, degenerate and unsupported field boundaries are rejected', () => {
  for (const input of [null, corners.slice(0, 3), [...corners, corners[1]], [corners[0], corners[2], corners[1], corners[3]], [[0, 0], [1, 0], [2, 0], [3, 0]], [[181, 0], [1, 1], [2, 2], [3, 3]], [['32', 46], ...corners.slice(1)]]) assert.throws(() => fieldBoundary(input));
});
