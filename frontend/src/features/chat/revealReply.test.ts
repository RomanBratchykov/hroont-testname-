import { test } from 'node:test';
import assert from 'node:assert/strict';
import { revealReply } from './revealReply.ts';

test('new replies publish word prefixes with sentence pauses instead of a complete answer', async () => {
    const visible: string[] = [];
    const delays: number[] = [];
    await revealReply('Hello farmer.\n\nYour field is ready.', value => visible.push(value), new AbortController().signal,
        async milliseconds => { delays.push(milliseconds); });
    assert.equal(visible[0], 'Hello ');
    assert.equal(visible[1], 'Hello farmer.\n\n');
    assert.equal(visible.at(-1), 'Hello farmer.\n\nYour field is ready.');
    assert.equal(visible.length, 6);
    assert.equal(delays[0], 150);
    assert.equal(delays[2], 550);
    assert.ok(visible.slice(0, -1).every(value => value !== visible.at(-1)));
});

test('stopping a reply prevents remaining words from appearing', async () => {
    const abort = new AbortController();
    const visible: string[] = [];
    await assert.rejects(revealReply('One two three four', value => {
        visible.push(value);
        if (visible.length === 2) abort.abort();
    }, abort.signal, async () => {}));
    assert.deepEqual(visible, ['One ', 'One two ']);
});

test('the actual timer keeps later words hidden until their scheduled delay', async context => {
    context.mock.timers.enable({ apis: ['setTimeout'] });
    const visible: string[] = [];
    const task = revealReply('Hello farmer.', value => visible.push(value), new AbortController().signal);
    context.mock.timers.tick(149);
    await Promise.resolve();
    assert.deepEqual(visible, []);
    context.mock.timers.tick(1);
    await Promise.resolve();
    assert.deepEqual(visible, ['Hello ']);
    context.mock.timers.tick(149);
    await Promise.resolve();
    assert.deepEqual(visible, ['Hello ']);
    context.mock.timers.tick(1);
    await task;
    assert.deepEqual(visible, ['Hello ', 'Hello farmer.']);
});
