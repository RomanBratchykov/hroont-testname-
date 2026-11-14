import { useEffect, useRef } from 'react';
import { Icon } from '../../../components/Icon';
export function Composer({ value, onChange, onSend }: {
    value: string;
    onChange: (value: string) => void;
    onSend: (value: string) => void;
}) {
    const input = useRef<HTMLTextAreaElement>(null);
    useEffect(() => {
        if (!input.current)
            return;
        input.current.style.height = 'auto';
        input.current.style.height = `${Math.min(input.current.scrollHeight, 220)}px`;
    }, [value]);
    return <form className="composer" onSubmit={e => { e.preventDefault(); if (value.trim())
        onSend(value); }}>
    <textarea ref={input} aria-label="Message Hroont" placeholder="Where shall we start?" value={value} rows={2} onChange={e => onChange(e.target.value)} onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                if (value.trim())
                    onSend(value);
            }
        }}/>
    <div className="composer-toolbar"><span className="composer-mode"><Icon name="leaf" size={15}/> A little room to think</span><button className="send-button" type="submit" disabled={!value.trim()} aria-label="Send message"><Icon name="arrow" size={20}/></button></div>
  </form>;
}
