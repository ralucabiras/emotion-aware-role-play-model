import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../services/api'
import type { SessionSummary, UserProfile } from '../types/api'

export function SettingsPage({user, onUser, onBack, onSignedOut}: {user: UserProfile; onUser: (user: UserProfile) => void; onBack: () => void; onSignedOut: () => void}) {
  const [profile, setProfile] = useState({first_name:user.first_name, last_name:user.last_name, preferred_name:user.preferred_name, country:user.country, timezone:user.timezone})
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [microphone, setMicrophone] = useState(localStorage.getItem('affectlab_microphone_enabled') !== 'false')
  const [currentPassword, setCurrentPassword] = useState(''), [newPassword, setNewPassword] = useState(''), [confirmPassword, setConfirmPassword] = useState('')
  const [profileMessage, setProfileMessage] = useState(''), [passwordMessage, setPasswordMessage] = useState(''), [busy, setBusy] = useState(false)

  useEffect(() => { void api.listSessions().then(setSessions) }, [])
  function field(name: keyof typeof profile, value: string) { setProfile(previous => ({...previous, [name]:value})) }
  async function saveProfile(event: FormEvent) { event.preventDefault(); setBusy(true); setProfileMessage(''); try { const updated = await api.updateProfile(profile); onUser(updated); setProfileMessage('Profile saved.') } catch (caught) { setProfileMessage(caught instanceof Error ? caught.message : 'Profile could not be saved.') } finally { setBusy(false) } }
  async function changePassword(event: FormEvent) {
    event.preventDefault(); setPasswordMessage('')
    if (newPassword !== confirmPassword) { setPasswordMessage('New passwords do not match.'); return }
    setBusy(true)
    try { await api.changePassword(currentPassword, newPassword); api.clearToken(); onSignedOut() }
    catch (caught) { setPasswordMessage(caught instanceof Error ? caught.message : 'Password could not be changed.') } finally { setBusy(false) }
  }
  function setMicrophonePreference(value: boolean) { setMicrophone(value); localStorage.setItem('affectlab_microphone_enabled', String(value)) }
  async function removeSession(id: string) { if (!confirm('Delete this session permanently?')) return; await api.deleteSession(id); setSessions(current => current.filter(session => session.session_id !== id)) }

  return <main className="settings-shell">
    <header><button className="brand-link" onClick={onBack}><span className="brand-mark">A</span><span className="brand">AffectLab</span></button><button className="text-button" onClick={onBack}>← Back to workspace</button></header>
    <section className="settings-heading"><p className="eyebrow">Account settings</p><h1>Your profile and privacy.</h1><p>Manage personal details, voice preferences, saved sessions, and account security.</p></section>
    <div className="settings-grid">
      <section className="settings-card"><p className="eyebrow">Profile</p><h2>Personal details</h2><form className="settings-form" onSubmit={saveProfile}><div className="form-row"><label>First name<input value={profile.first_name} onChange={event => field('first_name',event.target.value)} required maxLength={80}/></label><label>Last name<input value={profile.last_name} onChange={event => field('last_name',event.target.value)} required maxLength={80}/></label></div><label>Preferred name<input value={profile.preferred_name} onChange={event => field('preferred_name',event.target.value)} maxLength={80}/></label><label>Email<input value={user.email} disabled/><small>Email changes require a separate confirmation flow and are not currently available.</small></label><div className="form-row"><label>Country<input value={profile.country} onChange={event => field('country',event.target.value)} maxLength={80}/></label><label>Timezone<input value={profile.timezone} onChange={event => field('timezone',event.target.value)} required maxLength={80}/></label></div>{profileMessage && <p className="settings-message" role="status">{profileMessage}</p>}<button className="primary" disabled={busy}>Save profile</button></form></section>
      <section className="settings-card"><p className="eyebrow">Voice and privacy</p><h2>Microphone preference</h2><label className="preference-row"><span><strong>Enable optional voice input</strong><small>Recording still starts only when you press Add voice.</small></span><input type="checkbox" checked={microphone} onChange={event => setMicrophonePreference(event.target.checked)}/></label><div className="privacy-summary"><p>Text may be stored locally for up to 30 days and sent to OpenAI when configured.</p><p>Optional audio may be sent to OpenAI for transcription and processed locally for affect inference. AffectLab does not persist recordings.</p><p>Emotion estimates are uncertain and are not diagnoses.</p></div></section>
      <section className="settings-card"><p className="eyebrow">Security</p><h2>Change password</h2><form className="settings-form" onSubmit={changePassword}><label>Current password<input type="password" autoComplete="current-password" minLength={10} value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} required/></label><label>New password<input type="password" autoComplete="new-password" minLength={10} value={newPassword} onChange={event => setNewPassword(event.target.value)} required/></label><label>Confirm new password<input type="password" autoComplete="new-password" minLength={10} value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} required/></label>{passwordMessage && <p className="settings-message error" role="alert">{passwordMessage}</p>}<button className="primary" disabled={busy}>Change password and sign out</button></form></section>
      <section className="settings-card sessions-settings"><p className="eyebrow">Stored locally</p><h2>Sessions</h2>{sessions.length ? <div className="settings-session-list">{sessions.map((session,index) => <article key={session.session_id}><div><strong>Session {sessions.length-index}</strong><small>{new Date(session.updated_at).toLocaleString()} · {session.turn_count} turns{session.roleplay ? ` · ${session.roleplay.scenario_id}` : ''}</small></div><button onClick={() => removeSession(session.session_id)}>Delete</button></article>)}</div> : <p>No active sessions are stored.</p>}</section>
      <section className="settings-card danger-zone"><p className="eyebrow">Danger zone</p><h2>Delete account</h2><p>This permanently removes the account, saved sessions, and refresh tokens.</p><button onClick={async () => { if (confirm('Permanently delete your AffectLab account and every session?')) { await api.deleteAccount(); onSignedOut() } }}>Delete my account</button></section>
    </div>
  </main>
}
