import { useEffect, useRef } from 'react';
import demo, { showcaseInputs as inputs } from '../../config/showcase';
import { Icon } from '../../components/Icon';
import { SavedUserProfile } from './SavedUserProfile';

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
  ] }, {
    id: 'history', title: 'Synthetic crop history', fields: inputs.crop_history.records.map(row => ({ label: String(row.harvest_year), value: `${row.crop.replaceAll('_', ' ')} · ${row.yield.value} ${row.yield.unit} · sowing ${row.sowing_date}, harvest ${row.harvest_date} (assumed dates)` })),
  }, {
    id: 'management', title: 'Management and planning assumptions', fields: [
      { label: 'Tillage', value: `${inputs.management.tillage.type.replaceAll('_', ' ')} · ${inputs.management.tillage.typical_depth.value} cm` },
      { label: 'Residue cover', value: `${inputs.management.residue.assumed_cover.value}% (synthetic)` },
      { label: 'Planning', value: `${inputs.planning.start_harvest_year}–${inputs.planning.end_harvest_year} · ${inputs.planning.priority}` },
      { label: 'Included crops', value: inputs.crop_preferences.include.map(crop => crop.replaceAll('_', ' ')).join(', ') },
      { label: 'Excluded crops', value: inputs.crop_preferences.exclude.map(crop => crop.replaceAll('_', ' ')).join(', ') },
      { label: 'Support practices', value: inputs.management.support_practices.note },
      { label: 'Operations', value: inputs.operations.available.join(', ') + '; contractors available (synthetic)' },
      { label: 'Storage', value: `${inputs.operations.storage.capacity.value} ${inputs.operations.storage.capacity.unit} (synthetic)` },
      { label: 'Safety and access', value: inputs.operations.field_access.restrictions },
    ],
  }, {
    id: 'soil', title: 'Synthetic soil inputs — not lab results', fields: inputs.soil.layers.map(layer => ({ label: `${layer.depth.top}–${layer.depth.bottom} cm`, value: `Sand ${layer.sand.value}, silt ${layer.silt.value}, clay ${layer.clay.value} g/kg; organic carbon ${layer.organic_carbon.value} g/kg; pH ${layer.ph_h2o.value}; bulk density ${layer.bulk_density.value} g/cm³` })),
  }, {
    id: 'economics', title: 'Illustrative economic inputs — not market quotes', fields: [
      { label: 'Budget', value: `${inputs.economics.annual_budget.value} ${inputs.economics.annual_budget.unit} (synthetic)` },
      { label: 'Price and cost year', value: String(inputs.economics.price_year) },
      ...Object.entries(inputs.economics.crop_assumptions).map(([crop, values]) => ({ label: crop.replaceAll('_', ' '), value: `Yield ${values.yield.value} ${values.yield.unit}; price ${values.price.value} ${values.price.unit}; variable cost ${values.variable_cost.value} ${values.variable_cost.unit}` })),
      { label: 'Limits', value: inputs.economics.use_policy },
    ],
  }] }, onBack }: { data?: PersonalStateData | null; onBack: () => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  return <section className="workspace-page" aria-labelledby="personal-state-title">
    <button className="quiet-button page-back" onClick={onBack}>← Back to chat</button>
    <header className="page-heading"><p className="page-eyebrow">Your workspace</p><h1 ref={heading} tabIndex={-1} id="personal-state-title">Personal state</h1><p>Your saved farm information and field boundary, followed by the separate synthetic example profile.</p></header>
    <SavedUserProfile />{data && data.sections.length > 0 ? <div className="personal-sections">{data.sections.map(section => <section className="personal-section" key={section.id}><h2>{section.title}</h2><dl>{section.fields.map(field => <div key={field.label}><dt>{field.label}</dt><dd>{field.value || 'Not provided'}</dd></div>)}</dl></section>)}{data.updatedAt && <p className="settings-saved">Last updated: {data.updatedAt}</p>}</div> : <div className="personal-empty"><span className="personal-empty-icon"><Icon name="user" size={28} /></span><h2>No interview information yet</h2><p>Your personal information and interview summary will appear here when they become available.</p><span className="personal-status">Awaiting interview data</span></div>}
  </section>;
}
