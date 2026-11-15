import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readEvents } from './api.ts';

test('NDJSON stream preserves split UTF-8 and reports incomplete streams', async () => {
    const bytes = new TextEncoder().encode('{"type":"status","stage":"processing","message":"…"}\n{"type":"answer","content":"Hello","status":"completed"}\n');
    const stream = new ReadableStream<Uint8Array>({start(controller) {
        for (let i = 0; i < bytes.length; i += 2) controller.enqueue(bytes.slice(i, i + 2));
        controller.close();
    }});
    const result = [];
    for await (const event of readEvents(new Response(stream))) result.push(event);
    assert.equal(result[0].message, '…');
    assert.equal(result[1].content, 'Hello');
    await assert.rejects(async () => {
        for await (const event of readEvents(new Response('{"type":"status","message":"Waiting"}\n'))) void event;
    }, /interrupted/i);
});

test('API errors and malformed events do not appear as assistant success', async () => {
    await assert.rejects(async () => {
        for await (const event of readEvents(new Response(JSON.stringify({ detail: [{ msg: 'Unsupported format; paste the relevant text.' }] }), { status: 422 }))) void event;
    }, /paste the relevant text/);
    await assert.rejects(async () => {
        for await (const event of readEvents(new Response('{"detail":"Already processing"}', {status: 409}))) void event;
    }, /Already processing/);
    await assert.rejects(async () => {
        for await (const event of readEvents(new Response('{"type":"answer"}\n'))) void event;
    }, /invalid/i);
});
