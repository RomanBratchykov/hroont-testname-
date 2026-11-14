import { useState } from 'react';
import { Logo } from '../../components/Logo';
export function AuthScreen({ onContinue, openSettings }: { onContinue: () => void; openSettings: () => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  return <main className="auth-screen"><header className="entry-header"><Logo /><button className="quiet-button" onClick={openSettings}>Settings</button></header>
    <section className="auth-card" aria-labelledby="auth-title"><h1 id="auth-title">{mode === 'login' ? 'Welcome back.' : 'Make yourself at home.'}</h1><p className="auth-description">Your personal soil inspector.</p>
      <div className="auth-tabs" role="group" aria-label="Account options"><button type="button" aria-pressed={mode === 'login'} className={mode === 'login' ? 'selected' : ''} onClick={() => setMode('login')}>Log in</button><button type="button" aria-pressed={mode === 'register'} className={mode === 'register' ? 'selected' : ''} onClick={() => setMode('register')}>Register</button></div>
      <form key={mode} onSubmit={event => { event.preventDefault(); onContinue(); }}>
        <label htmlFor="email">Email</label><input id="email" type="email" name="email" autoComplete="email" placeholder="you@example.com" required />
        <label htmlFor="password">Password</label><input id="password" type="password" name="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'register' ? 8 : 1} required />
        {mode === 'register' && <p className="field-hint">Use at least 8 characters.</p>}
        <button className="primary-button" type="submit">{mode === 'login' ? 'Preview log in' : 'Preview registration'}</button>
      </form>
      <p className="auth-preview-note">Preview</p>
      <button className="quiet-button preview-entry" onClick={onContinue}>Explore without an account <span aria-hidden="true">→</span></button>
    </section>
  </main>;
}
