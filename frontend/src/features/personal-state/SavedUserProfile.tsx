import { useEffect, useState } from 'react';
import { command } from '../chat/api';
import { BoundaryPreview } from '../field-dashboard/BoundaryPreview';
import { isUserProfile, type UserProfile } from './profile';

export function SavedUserProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (import.meta.env.VITE_CHAT_BACKEND !== 'on') return;
    const abort = new AbortController();
    void command({ action: 'profile' }, abort.signal).then(value => {
      if (!isUserProfile(value)) throw new Error('Could not read the saved profile.');
      if (!abort.signal.aborted) setProfile(value);
    }).catch(reason => { if (!abort.signal.aborted) setError(reason instanceof Error ? reason.message : 'Could not load profile.'); });
    return () => abort.abort();
  }, []);
  return <section className="personal-section"><h2>Your saved information</h2>{error ? <p role="alert">{error}</p> : profile ? <>
    <dl>{Object.entries(profile.facts).map(([name, value]) => <div key={name}><dt>{name.replaceAll('_', ' ')}</dt><dd>{value}</dd></div>)}</dl>
    {profile.boundary && <BoundaryPreview text={JSON.stringify(profile.boundary)}/>}
    {profile.updated_at ? <p>Saved {new Date(profile.updated_at * 1000).toLocaleString()} · Farmer-reported, unverified.</p> : <p>No saved information yet. Tell Soily about your farm or save a field boundary on the dashboard.</p>}
    <p>Stored for this browser session across chats and reloads. Clearing browser cookies loses access to this profile.</p>
  </> : <p>{import.meta.env.VITE_CHAT_BACKEND === 'on' ? 'Loading saved information…' : 'Connect the backend to save your information.'}</p>}</section>;
}
