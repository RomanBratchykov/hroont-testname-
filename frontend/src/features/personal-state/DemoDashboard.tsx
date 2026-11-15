import { useEffect, useRef } from 'react';
import demo, { showcaseInputs } from '../../config/showcase';

export function DemoDashboard({ onAsk }: { onAsk: (question: string) => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(showcaseInputs, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'croptato-john-showcase-inputs.json';
    link.click();
    URL.revokeObjectURL(url);
  };
  return <section className="workspace-page" aria-labelledby="dashboard-title">
    <header className="page-heading"><p className="page-eyebrow">Saved example · Test account</p><h1 id="dashboard-title" ref={heading} tabIndex={-1}>John’s field, at a glance</h1><p>{demo.status}. These examples remain available after restarting Croptato.</p></header>
    <section className="personal-section demo-profile" aria-label="Demonstration field">
      <h2>{demo.accountName} · {demo.location}</h2>
      <dl><div><dt>Field size</dt><dd>Approximately {demo.areaHa} ha · synthetic</dd></div><div><dt>Water</dt><dd>{demo.water}</dd></div><div><dt>Crop history</dt><dd>{demo.cropHistory}</dd></div><div><dt>Soil</dt><dd>{demo.soil}</dd></div></dl>
    </section>
    <div className="demo-strategies">{demo.strategies.map(strategy => <section className="personal-section" key={strategy.id}>
      <p className="page-eyebrow">Illustrative rotation · Not validated</p><h2>{strategy.title}</h2><p className="demo-description">{strategy.description}</p>
      <ol className="demo-rotation">{strategy.crops.map((crop, index) => <li key={index}><span>Year {index + 1}</span><strong>{crop}</strong></li>)}</ol>
      <button className="quiet-button" onClick={() => onAsk(`Explain John’s ${strategy.title} example and which data or checks are missing before it could be recommended.`)}>Ask Soily about this example →</button>
    </section>)}</div>
    <section className="personal-section demo-limitations"><h2>What this example can tell you</h2><p className="demo-description">Explore the presentation and discuss assumptions with Soily. Scientific results remain unavailable until the analysis tools and required inputs are connected.</p><ul>{demo.limitations.map(text => <li key={text}>{text}</li>)}</ul><p className="settings-saved">Source: {demo.source}. John is the test persona added for this presentation.</p></section>
    <div className="demo-actions"><button className="quiet-button" onClick={download}>Download example data</button><button className="quiet-button" onClick={() => onAsk('What might change in John’s example if irrigation became available? Explain the assumptions and missing data without claiming a calculated result.')}>Discuss a change with Soily →</button></div>
  </section>;
}
