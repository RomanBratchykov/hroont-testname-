import { useEffect, useRef } from 'react';
import demo from '../../config/demo.json';
import { Icon } from '../../components/Icon';

/** Shared demonstration profile; visitor chats remain separate. */
export interface PersonalStateData {
  updatedAt: string | null;
  sections: { id: string; title: string; fields: { label: string; value: string }[] }[];
}
export function PersonalStatePage({ data = { updatedAt: null, sections: [{ id: 'john', title: 'John’s test profile', fields: [
    { label: 'Account', value: demo.accountName + ' — ' + demo.accountType },
    { label: 'Location', value: demo.location },
    { label: 'Field area', value: `Approximately ${demo.areaHa} ha (synthetic)` },
    { label: 'Water', value: demo.water },
    { label: 'Crop history', value: demo.cropHistory },
    { label: 'Soil', value: demo.soil },
    { label: 'Data status', value: demo.status },
  ] }] }, onBack }: { data?: PersonalStateData | null; onBack: () => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  return <section className="workspace-page" aria-labelledby="personal-state-title">
    <button className="quiet-button page-back" onClick={onBack}>← Back to chat</button>
    <header className="page-heading"><p className="page-eyebrow">Your workspace</p><h1 ref={heading} tabIndex={-1} id="personal-state-title">Personal state</h1><p>John’s saved demonstration profile. Example assumptions are shown explicitly.</p></header>
    {data && data.sections.length > 0 ? <div className="personal-sections">{data.sections.map(section => <section className="personal-section" key={section.id}><h2>{section.title}</h2><dl>{section.fields.map(field => <div key={field.label}><dt>{field.label}</dt><dd>{field.value || 'Not provided'}</dd></div>)}</dl></section>)}{data.updatedAt && <p className="settings-saved">Last updated: {data.updatedAt}</p>}</div> : <div className="personal-empty"><span className="personal-empty-icon"><Icon name="user" size={28} /></span><h2>No interview information yet</h2><p>Your personal information and interview summary will appear here when they become available.</p><span className="personal-status">Awaiting interview data</span></div>}
  </section>;
}
