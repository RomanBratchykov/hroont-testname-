export interface ChatEvent {
    type: 'status' | 'answer' | 'error';
    stage?: string;
    message?: string;
    content?: string;
    status?: string;
    code?: string;
    evidence?: unknown[];
}

export async function* readEvents(response: Response): AsyncGenerator<ChatEvent> {
    if (!response.ok) {
        const body: unknown = await response.json().catch(() => null);
        const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null;
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}).`);
    }
    if (!response.body) throw new Error('Response has no readable stream.');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let terminal = false;
    try {
        while (true) {
            const { done, value } = await reader.read();
            buffer += decoder.decode(value, { stream: !done });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';
            if (done && buffer.trim()) lines.push(buffer);
            for (const line of lines) {
                if (!line.trim()) continue;
                const event: unknown = JSON.parse(line);
                if (!event || typeof event !== 'object' || !('type' in event) ||
                    !['status', 'answer', 'error'].includes(String(event.type)) ||
                    (event.type === 'answer' && (!('content' in event) || typeof event.content !== 'string'))) {
                    throw new Error('Invalid server event.');
                }
                const parsed = event as ChatEvent;
                if (parsed.type === 'answer' || parsed.type === 'error') terminal = true;
                yield parsed;
            }
            if (done) break;
        }
        if (!terminal) throw new Error('Connection interrupted before the answer finished. Send again to retry.');
    } finally {
        reader.releaseLock();
    }
}

export async function command(body: Record<string, unknown>, signal?: AbortSignal): Promise<unknown> {
    const response = await fetch('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body), signal,
    });
    if (!response.ok) {
        const data: unknown = await response.json().catch(() => null);
        throw new Error(data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string'
            ? data.detail : `Request failed (${response.status}).`);
    }
    return response.json();
}

export interface Upload { name: string; data: string }
export async function encodeFiles(files: File[]): Promise<Upload[]> {
    if (files.length > 3 || files.some(file => file.size > 10 * 1024 * 1024)) {
        throw new Error('Attach up to three files, maximum 10 MB each.');
    }
    return Promise.all(files.map(file => new Promise<Upload>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve({ name: file.name, data: String(reader.result).split(',')[1] });
        reader.onerror = () => reject(new Error('Could not read the file.'));
        reader.readAsDataURL(file);
    })));
}
