import { useEffect, useRef, useState } from 'react';
import { Icon } from '../../../components/Icon';
import { ModelSelector } from './ModelSelector';
export function Composer({ value, onChange, onSend, busy = false, disabled = false, connected = false, onStop }: {
    value: string;
    onChange: (value: string) => void;
    onSend: (value: string, files?: File[]) => void;
    busy?: boolean; disabled?: boolean; connected?: boolean; onStop?: () => void;
}) {
    const [files, setFiles] = useState<File[]>([]);
    const submit = () => { if (!busy && !disabled && (value.trim() || files.length)) { onSend(value, files); setFiles([]); } };
    const input = useRef<HTMLTextAreaElement>(null);
    useEffect(() => {
        if (!input.current)
            return;
        input.current.style.height = 'auto';
        input.current.style.height = `${Math.min(input.current.scrollHeight, 220)}px`;
    }, [value]);
    return <form className="composer" onSubmit={e => { e.preventDefault(); submit(); }}>
    <textarea ref={input} aria-label="Message Hroont" placeholder="Where shall we start?" value={value} rows={2} onChange={e => onChange(e.target.value)} onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                submit();
            }
        }}/>
    {files.length > 0 && <p className="field-hint">{files.map(file => file.name).join(", ")} <button type="button" className="quiet-button" onClick={() => setFiles([])}>Remove</button></p>}
    <div className="composer-toolbar"><div className="composer-tools"><ModelSelector /><label className="icon-button file-picker" title="Attach files"><Icon name="paperclip" /><input aria-label="Attach files" type="file" accept=".md,.txt,.json,.xlsx" multiple disabled={!connected || busy || disabled} onChange={event => setFiles(Array.from(event.target.files ?? []))} /></label></div>{busy ? <button type="button" className="quiet-button" onClick={onStop}>Stop</button> : <button className="send-button" type="submit" disabled={disabled || (!value.trim() && !files.length)} aria-label="Send message"><Icon name="arrow" size={20}/></button>}</div>
  </form>;
}
