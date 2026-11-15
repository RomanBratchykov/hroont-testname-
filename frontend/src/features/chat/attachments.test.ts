import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateFiles } from './attachments.ts';

test('text attachments accept uppercase extensions and reject binary formats explicitly', () => {
    for (const name of ['field.JSON', 'field.geojson', 'notes.txt', 'notes.md', 'data.csv', 'data.tsv']) {
        assert.doesNotThrow(() => validateFiles([new File(['text'], name)]));
    }
    for (const name of ['photo.png', 'report.pdf', 'field.xlsx', 'data.json.exe']) {
        assert.throws(() => validateFiles([new File(['text'], name)]), /paste the relevant text/);
    }
    assert.throws(() => validateFiles(Array.from({ length: 4 }, () => new File(['a'], 'a.txt'))), /three files/);
});
