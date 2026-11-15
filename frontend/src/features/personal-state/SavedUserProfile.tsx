import { useEffect, useState } from 'react';
import { command } from '../chat/api';
import { BoundaryPreview } from '../field-dashboard/BoundaryPreview';
import { isUserProfile, type UserProfile } from './profile';

export function SavedUserProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [facts, setFacts] = useState<Record<string, string>>({});
  const [newName, setNewName] = useState('');
  const [newValue, setNewValue] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (import.meta.env.VITE_CHAT_BACKEND !== 'on') return;
    const abort = new AbortController();
    void command({ action: 'profile' }, abort.signal).then(value => {
      if (!isUserProfile(value)) throw new Error('Could not read the saved profile.');
      if (!abort.signal.aborted) { setProfile(value); setFacts(value.facts); }
    }).catch(reason => { if (!abort.signal.aborted) setError(reason instanceof Error ? reason.message : 'Could not load profile.'); });
    return () => abort.abort();
  }, []);
  const update = async (clear: boolean) => {
    setBusy(true); setError(''); setNotice('');
    try {
      const patch = { ...facts, ...(newName.trim() && newValue.trim() ? { [newName.trim()]: newValue.trim() } : {}) };
      const value = await command(clear ? { action: 'clear_profile' } : { action: 'save_profile', profile: { facts: patch } });
      if (!isUserProfile(value)) throw new Error('The server did not confirm the profile update.');
      setProfile(value); setFacts(value.facts); setNewName(''); setNewValue('');
      setNotice(clear ? 'All profile information and the field boundary were cleared.' : 'Your information was saved.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update the profile.'); }
    finally { setBusy(false); }
  };
  return <section className="personal-section"><h2>Your current information</h2>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {profile ? <>
      {!Object.keys(profile.facts).length && !profile.boundary && <p>Your profile is empty. Add your information below or tell Soily about your farm.</p>}
      <form onSubmit={event => { event.preventDefault(); void update(false); }}>
        <fieldset disabled={busy}><legend>Farm details</legend>
          {Object.entries(facts).map(([name, value]) => <label key={name} style={{ display: 'grid', gap: 6, marginBottom: 12 }}>{name.replaceAll('_', ' ')}<input aria-label={name.replaceAll('_', ' ')} value={value} maxLength={400} required onChange={event => setFacts(previous => ({ ...previous, [name]: event.target.value }))}/></label>)}
          <label>Additional detail name<input value={newName} maxLength={60} onChange={event => setNewName(event.target.value)} required={!!newValue.trim()}/></label>
          <label>Additional detail value<input value={newValue} maxLength={400} onChange={event => setNewValue(event.target.value)} required={!!newName.trim()}/></label>
          <button type="submit" className="quiet-button" disabled={!Object.keys(facts).length && !(newName.trim() && newValue.trim())}>{busy ? 'Saving...' : 'Save changes'}</button>
        </fieldset>
      </form>
      {profile.boundary && <><BoundaryPreview text={JSON.stringify(profile.boundary)}/><a href="#/dashboard">Change field boundary</a></>}
      <button type="button" className="quiet-button" disabled={busy} onClick={() => { void update(true); }}>Clear all information and field boundary</button>
      {profile.updated_at && <p>Saved {new Date(profile.updated_at * 1000).toLocaleString()} - unverified farm inputs.</p>}
      <p>Stored for this browser across chats and reloads. Clearing browser cookies loses access.</p>
    </> : <p>{import.meta.env.VITE_CHAT_BACKEND === 'on' ? 'Loading saved information...' : 'Connect the backend to save your information.'}</p>}
  </section>;
}
