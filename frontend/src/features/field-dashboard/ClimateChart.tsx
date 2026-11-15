import { useState } from 'react';
import type { ClimateData } from './types';

const VARIABLES = [
  ['T2M', 'Mean temperature'], ['PRECTOTCORR', 'Rainfall'], ['T2M_MAX', 'Daily maximum temperature'],
  ['T2M_MIN', 'Daily minimum temperature'], ['RH2M', 'Relative humidity'], ['WS2M', 'Wind at 2 m'], ['ALLSKY_SFC_SW_DWN', 'Solar radiation'],
];
export function ClimateChart({ data }: { data: ClimateData }) {
  const [variable, setVariable] = useState('T2M');
  const [year, setYear] = useState('2025');
  const [active, setActive] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const months = data.months.filter(m => year === 'all' || m.period.startsWith(year));
  const values = months.map(m => m.values[variable]);
  const valid = values.filter((v): v is number => v !== null && v !== undefined);
  const lower = Math.min(0, ...valid), upper = Math.max(1, ...valid);
  const range = upper - lower || 1;
  const y = (v: number) => 245 - (v - lower) / range * 205;
  const x = (i: number) => 60 + (i + 0.5) / months.length * 690;
  const unit = data.units[variable];
  const chosen = active !== null ? months[active] : null;
  return <>
    <div className="chart-controls"><label>Variable<select value={variable} onChange={e => { setVariable(e.target.value); setActive(null); }}>{VARIABLES.map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label><label>Period<select value={year} onChange={e => { setYear(e.target.value); setActive(null); }}><option value="all">2016–2025</option>{Array.from({ length: 10 }, (_, i) => String(2025 - i)).map(y => <option key={y}>{y}</option>)}</select></label><button className="quiet-button" aria-expanded={table} onClick={() => setTable(v => !v)}>{table ? 'Hide data table' : 'View data table'}</button></div>
    <div className="chart-readout" aria-live="polite">{chosen ? <><strong>{chosen.period}</strong><span>{chosen.values[variable] === null ? 'Missing / incomplete' : `${chosen.values[variable]} ${unit}`}</span><small>{chosen.coverage[variable]} / {chosen.days} valid days</small></> : <span>Hover, tap, or focus a month to inspect its value · {unit}</span>}</div>
    <svg className="climate-chart" viewBox="0 0 800 290" role="group" aria-label={`${VARIABLES.find(v => v[0] === variable)?.[1]}, ${year}, ${unit}`}>
      {Array.from({ length: 5 }, (_, i) => {
        const value = lower + range * i / 4;
        return <g key={i}><line x1="60" x2="750" y1={y(value)} y2={y(value)} stroke="var(--outline)" /><text x="48" y={y(value) + 4} textAnchor="end">{value.toFixed(1)}</text></g>;
      })}
      {months.map((month, i) => {
        const value = month.values[variable];
        const previous = months[i - 1]?.values[variable];
        const label = year === 'all' ? month.period.slice(0, 4) : new Date(`${month.period}-15T00:00:00Z`).toLocaleString('en', { month: 'short', timeZone: 'UTC' });
        return <g key={month.period} tabIndex={0} role="button" aria-label={`${month.period}: ${value === null ? 'missing' : `${value} ${unit}`}, ${month.coverage[variable]} of ${month.days} days`} onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onClick={() => setActive(i)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActive(i); } }}>
          <rect x={x(i) - 345 / months.length} width={690 / months.length} y="25" height="230" fill={active === i ? 'var(--highlight)' : 'transparent'} />
          {value !== null && value !== undefined ? variable === 'PRECTOTCORR' ? <rect x={x(i) - 220 / months.length} width={440 / months.length} y={y(value)} height={Math.max(1, y(0) - y(value))} rx="2" fill="#4781a4" /> : <>
            {i > 0 && previous !== null && previous !== undefined && <line x1={x(i - 1)} y1={y(previous)} x2={x(i)} y2={y(value)} stroke="#a76438" strokeWidth="2.5" pointerEvents="none" />}
            <circle cx={x(i)} cy={y(value)} r={months.length > 12 ? 2 : 4} fill="#a76438" pointerEvents="none" />
          </> : <text x={x(i)} y="240" textAnchor="middle">×</text>}
          {(year !== 'all' || i % 12 === 6) && <text x={x(i)} y="275" textAnchor="middle">{label}</text>}
        </g>;
      })}
    </svg>
    <p className="field-note">Monthly {variable === 'PRECTOTCORR' ? 'rainfall totals' : 'means of daily values'}. Gaps mean missing or incomplete months. Historical gridded estimates, not a forecast.</p>
    {table && <div className="climate-table"><table><caption>{VARIABLES.find(v => v[0] === variable)?.[1]} · NASA POWER · {unit}</caption><thead><tr><th>Month</th><th>Value ({unit})</th><th>Valid days</th></tr></thead><tbody>{months.map(m => <tr key={m.period}><th>{m.period}</th><td>{m.values[variable] ?? 'Missing'}</td><td>{m.coverage[variable]} / {m.days}</td></tr>)}</tbody></table></div>}
  </>;
}
