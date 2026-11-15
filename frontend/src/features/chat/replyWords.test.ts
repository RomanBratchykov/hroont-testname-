import { test } from 'node:test';
import assert from 'node:assert/strict';
import { replyWordDelay, replyWords } from './replyWords.ts';

test('replies reveal complete words and preserve spacing, line breaks and Unicode', () => {
    const text = '  Hello, farmer!\n\nYour field is 30 ha. 🌱';
    const words = replyWords(text);
    assert.equal(words[0], '  Hello, ');
    assert.equal(words[1], 'farmer!\n\n');
    assert.equal(words.join(''), text);
    assert.equal(words.at(-1), '🌱');
});

test('empty and whitespace-only replies remain intact', () => {
    assert.deepEqual(replyWords(''), []);
    assert.equal(replyWords(' \n\t').join(''), ' \n\t');
});

test('typing pauses at punctuation and paragraph breaks without rushing ordinary words', () => {
    assert.equal(replyWordDelay('field '), 150);
    assert.equal(replyWordDelay('field, '), 240);
    assert.equal(replyWordDelay('field.” '), 400);
    assert.equal(replyWordDelay('field!\n\n'), 550);
});
