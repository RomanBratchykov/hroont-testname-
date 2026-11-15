import { useEffect, useRef } from 'react';
import { FieldDashboard } from '../field-dashboard/FieldDashboard';
import { SavedUserProfile } from './SavedUserProfile';
import demo, { showcaseInputs } from '../../config/showcase';

export function DemoDashboard({ onAsk }: { onAsk: (question: string) => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(showcaseInputs, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url; link.download = 'croptato-starting-inputs.json'; link.click();
    URL.revokeObjectURL(url);
  };
  return <section className="workspace-page" aria-labelledby="dashboard-title">
    <header className="page-heading"><p className="page-eyebrow">Field intelligence</p><h1 id="dashboard-title" ref={heading} tabIndex={-1}>Your field, connected</h1><p>Explore your field, inspect its climate and calculate from your current inputs.</p></header>
    <FieldDashboard onAsk={onAsk}/>
    <SavedUserProfile/>
    <div className="demo-strategies">{demo.strategies.map(strategy => <section className="personal-section" key={strategy.id}>
      <p className="page-eyebrow">Draft rotation - requires checks</p><h2>{strategy.title}</h2><p className="demo-description">{strategy.description}</p>
      <ol className="demo-rotation">{strategy.crops.map((crop, index) => <li key={index}><span>Year {index + 1}</span><strong>{crop}</strong></li>)}</ol>
      <button className="quiet-button" onClick={() => onAsk(`Review the ${strategy.title} draft against my current saved inputs. Run the relevant calculation tools and explain any missing checks.`)}>Review this rotation with Soily</button>
    </section>)}</div>
    <details className="personal-section demo-limitations"><summary>Input details and calculation assumptions</summary><p>Your saved profile is editable. Draft rotations remain separate from completed analysis results.</p><ul>{demo.limitations.map(text => <li key={text}>{text}</li>)}</ul><p>{demo.source}</p><button className="quiet-button" onClick={download}>Download original starting inputs and provenance</button></details>
    <div className="demo-actions"><button className="quiet-button" onClick={() => onAsk('What changes if irrigation becomes available for my current field? Use my saved inputs and the connected tools, and identify any missing data.')}>Explore a change with Soily</button></div>
  </section>;
}
