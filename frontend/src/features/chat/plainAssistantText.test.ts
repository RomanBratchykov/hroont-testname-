import { test } from 'node:test';
import assert from 'node:assert/strict';
import { plainAssistantText } from './plainAssistantText.ts';

test('assistant text removes all double-asterisk markers while retaining content', () => {
    assert.equal(plainAssistantText('**Chickpea**: **12,800 UAH/ha**.\n**Missing inputs'), 'Chickpea: 12,800 UAH/ha.\nMissing inputs');
    assert.equal(plainAssistantText('2 * 3 = 6\nField: 30 ha.'), '2 * 3 = 6\nField: 30 ha.');
});
