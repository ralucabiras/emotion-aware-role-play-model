import { Component, useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Dashboard } from './components/Dashboard'
import { Onboarding } from './components/Onboarding'
import { HomeDashboard } from './components/HomeDashboard'
import { SettingsPage } from './components/SettingsPage'
import { api } from './services/api'
import type { UserProfile } from './types/api'
import './styles.css'

function navigate(path: string) { history.pushState({}, '', path); window.dispatchEvent(new PopStateEvent('popstate')) }
function usePath() {
  const [path, setPath] = useState(location.pathname + location.search)
  useEffect(() => { const update = () => setPath(location.pathname + location.search); addEventListener('popstate', update); return () => removeEventListener('popstate', update) }, [])
  return path
}

export class AppErrorBoundary extends Component<{children: ReactNode}, {error: string}> {
  state = { error: '' }
  static getDerivedStateFromError(error: unknown) { return { error: error instanceof Error ? error.message : 'Unexpected application error' } }
  render() {
    if (this.state.error) return <main className="error-page"><section><p className="eyebrow">AffectLab</p><h1>The workspace could not be displayed.</h1><p role="alert">{this.state.error}</p><button className="primary" onClick={() => { sessionStorage.removeItem('access_token'); location.assign('/login') }}>Return to sign in</button></section></main>
    return this.props.children
  }
}

function PublicNav({user}: {user?: UserProfile}) {
  return <nav className="public-nav"><button className="brand-link" onClick={() => navigate('/')}><span className="brand-mark">A</span><span className="brand">AffectLab</span></button><div><button onClick={() => navigate('/about')}>About us</button>{user ? <button className="nav-primary" onClick={() => navigate('/app')}>Open AffectLab</button> : <><button onClick={() => navigate('/login')}>Sign in</button><button className="nav-primary" onClick={() => navigate('/signup')}>Create account</button></>}</div></nav>
}

function Landing({user}: {user?: UserProfile}) {
  return <main className="public-shell"><PublicNav user={user}/><section className="hero"><div><p className="eyebrow">Reflect · Reframe · Rehearse</p><h1>Practise the conversation<br/>before it matters.</h1><p className="hero-copy">AffectLab is a private dissertation research prototype that helps you reflect on difficult conversations, rehearse clearer language, and receive evidence-based practice feedback.</p><div className="hero-actions"><button className="primary" onClick={() => navigate(user ? '/app' : '/signup')}>{user ? 'Open AffectLab' : 'Get started'}</button><button className="secondary" onClick={() => navigate('/about')}>How it works</button></div></div><div className="hero-card"><span>01</span><h2>Describe</h2><p>Share the situation in your own words.</p><span>02</span><h2>Rehearse</h2><p>Practise boundaries, workload conversations, and relationship needs.</p><span>03</span><h2>Reflect</h2><p>Review observable communication skills—not diagnoses or personality claims.</p></div></section><section className="public-note"><strong>Designed with uncertainty in mind.</strong><p>Affect estimates can be wrong. Crisis safeguards remain text-first, and AffectLab is not therapy, diagnosis, or emergency support.</p></section></main>
}

function About({user}: {user?: UserProfile}) {
  return <main className="public-shell"><PublicNav user={user}/><section className="about-hero"><p className="eyebrow">About the research</p><h1>A careful space for social rehearsal.</h1><p>AffectLab explores whether contextual text and vocal signals can support more adaptive role-play feedback. It was created as a dissertation research project and is not a commercial clinical product.</p></section><section className="about-grid"><article><h2>What we are studying</h2><p>How multimodal emotion recognition and transparent communication metrics can help people practise difficult conversations without presenting uncertain predictions as facts.</p></article><article><h2>What stays human</h2><p>You choose what to share, whether to use audio, when to pause, and when to delete a session. Automated estimates never define how you feel.</p></article><article><h2>Privacy boundaries</h2><p>Session text is stored locally for up to 30 days. Audio is opt-in, may be sent to OpenAI for transcription, is processed in memory for affect inference, and is not persisted by AffectLab.</p></article><article><h2>Safety boundaries</h2><p>AffectLab is not medical care. Text-based crisis checks take precedence over model output, and urgent situations should be directed to local emergency services.</p></article></section></main>
}

function AuthLayout({title, subtitle, children}: {title: string; subtitle: string; children: ReactNode}) { return <main className="auth-shell"><PublicNav/><section className="auth-card"><p className="eyebrow">AffectLab account</p><h1>{title}</h1><p>{subtitle}</p>{children}</section></main> }

function Login({onAuth}: {onAuth: (user: UserProfile) => void}) {
  const [email, setEmail] = useState(''), [password, setPassword] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(''); try { const result = await api.login(email, password); onAuth(result.user); navigate(result.user.onboarding_completed ? '/app' : '/onboarding') } catch (caught) { setError(caught instanceof Error ? caught.message : 'Sign in failed') } finally { setBusy(false) } }
  return <AuthLayout title="Welcome back." subtitle="Sign in to continue your private practice sessions."><form className="auth-form" onSubmit={submit}><label>Email<input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required/></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required/></label><button type="button" className="forgot-link" onClick={() => navigate('/forgot-password')}>Forgot your password?</button>{error && <p className="error" role="alert">{error}</p>}<button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form><button className="text-button" onClick={() => navigate('/signup')}>Need an account? Create one</button></AuthLayout>
}

function ForgotPassword() {
  const [email, setEmail] = useState(''), [message, setMessage] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(''); try { setMessage((await api.forgotPassword(email)).message) } catch (caught) { setError(caught instanceof Error ? caught.message : 'Request failed') } finally { setBusy(false) } }
  return <AuthLayout title="Reset your password." subtitle="Enter the email used for your AffectLab account.">{message ? <div className="auth-result" role="status"><div className="email-icon">✉</div><p>{message}</p><small>For privacy, this message is the same whether or not an account was found.</small></div> : <form className="auth-form" onSubmit={submit}><label>Email<input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required autoFocus/></label>{error && <p className="error" role="alert">{error}</p>}<button className="primary" disabled={busy}>{busy ? 'Sending…' : 'Send reset link'}</button></form>}<button className="text-button" onClick={() => navigate('/login')}>Return to sign in</button></AuthLayout>
}

function ResetPassword() {
  const token = new URLSearchParams(location.search).get('token') || '', [password, setPassword] = useState(''), [confirmation, setConfirmation] = useState(''), [error, setError] = useState(''), [done, setDone] = useState(false), [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) { event.preventDefault(); setError(''); if (password !== confirmation) { setError('Passwords do not match'); return } setBusy(true); try { await api.resetPassword(token, password); api.clearToken(); setDone(true) } catch (caught) { setError(caught instanceof Error ? caught.message : 'Password reset failed') } finally { setBusy(false) } }
  if (!token) return <AuthLayout title="Link not accepted." subtitle="This password reset link is incomplete."><button className="primary wide" onClick={() => navigate('/forgot-password')}>Request a new link</button></AuthLayout>
  if (done) return <AuthLayout title="Password updated." subtitle="Your existing signed-in sessions have been revoked. You can now sign in with your new password."><div className="verification-state success">✓</div><button className="primary wide" onClick={() => navigate('/login')}>Continue to sign in</button></AuthLayout>
  return <AuthLayout title="Choose a new password." subtitle="This link is single-use and expires after 30 minutes."><form className="auth-form" onSubmit={submit}><label>New password<input type="password" autoComplete="new-password" minLength={10} maxLength={128} value={password} onChange={event => setPassword(event.target.value)} required autoFocus/><small>At least 10 characters.</small></label><label>Confirm new password<input type="password" autoComplete="new-password" minLength={10} maxLength={128} value={confirmation} onChange={event => setConfirmation(event.target.value)} required/></label>{error && <p className="error" role="alert">{error}</p>}<button className="primary" disabled={busy}>{busy ? 'Updating…' : 'Update password'}</button></form><button className="text-button" onClick={() => navigate('/forgot-password')}>Request a new link</button></AuthLayout>
}

function Signup() {
  const [form, setForm] = useState({first_name:'', last_name:'', preferred_name:'', email:'', password:'', country:'', timezone:Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', consent:false}), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  function field(name: string, value: string | boolean) { setForm(previous => ({...previous, [name]: value})) }
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(''); try { await api.register(form); navigate(`/check-email?email=${encodeURIComponent(form.email)}`) } catch (caught) { setError(caught instanceof Error ? caught.message : 'Registration failed') } finally { setBusy(false) } }
  return <AuthLayout title="Create your account." subtitle="Only the profile details needed to personalise your experience are collected."><form className="auth-form" onSubmit={submit}><div className="form-row"><label>First name<input value={form.first_name} onChange={event => field('first_name', event.target.value)} required maxLength={80}/></label><label>Last name<input value={form.last_name} onChange={event => field('last_name', event.target.value)} required maxLength={80}/></label></div><label>Preferred name <span className="optional">Optional</span><input value={form.preferred_name} onChange={event => field('preferred_name', event.target.value)} maxLength={80}/></label><label>Email<input type="email" autoComplete="email" value={form.email} onChange={event => field('email', event.target.value)} required/></label><label>Password<input type="password" autoComplete="new-password" minLength={10} value={form.password} onChange={event => field('password', event.target.value)} required/><small>At least 10 characters.</small></label><div className="form-row"><label>Country <span className="optional">Optional</span><input value={form.country} onChange={event => field('country', event.target.value)} maxLength={80}/></label><label>Timezone<input value={form.timezone} onChange={event => field('timezone', event.target.value)} required maxLength={80}/></label></div><label className="consent"><input type="checkbox" checked={form.consent} onChange={event => field('consent', event.target.checked)} required/><span>I consent to take part in this dissertation research prototype and to the collection of pseudonymous questionnaire ratings, interaction events, and feedback metrics. Conversation text is retained locally for up to 30 days and may be sent to OpenAI when configured. Optional voice recordings may be sent to OpenAI for transcription but are not stored by AffectLab. AffectLab is not therapy or medical care.</span></label>{error && <p className="error" role="alert">{error}</p>}<button className="primary" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button></form><button className="text-button" onClick={() => navigate('/login')}>Already registered? Sign in</button></AuthLayout>
}

function CheckEmail() {
  const email = new URLSearchParams(location.search).get('email') || '', [message, setMessage] = useState('Check your inbox and open the confirmation link before signing in.'), [busy, setBusy] = useState(false)
  async function resend() { setBusy(true); try { setMessage((await api.resendVerification(email)).message) } finally { setBusy(false) } }
  return <AuthLayout title="Check your email." subtitle={message}><div className="email-icon">✉</div><p className="email-address">{email}</p><button className="primary wide" disabled={!email || busy} onClick={resend}>{busy ? 'Sending…' : 'Resend confirmation'}</button><button className="text-button" onClick={() => navigate('/login')}>Return to sign in</button></AuthLayout>
}

function VerifyEmail() {
  const token = new URLSearchParams(location.search).get('token') || '', [state, setState] = useState<'working'|'success'|'error'>(token ? 'working' : 'error'), [message, setMessage] = useState(token ? 'Confirming your email…' : 'This confirmation link is incomplete.')
  useEffect(() => { if (!token) return; void api.verifyEmail(token).then(result => { setState('success'); setMessage(result.message) }).catch(error => { setState('error'); setMessage(error instanceof Error ? error.message : 'Confirmation failed') }) }, [token])
  return <AuthLayout title={state === 'success' ? 'Email confirmed.' : state === 'error' ? 'Link not accepted.' : 'One moment.'} subtitle={message}><div className={`verification-state ${state}`}>{state === 'working' ? '…' : state === 'success' ? '✓' : '!'}</div><button className="primary wide" disabled={state === 'working'} onClick={() => navigate('/login')}>Continue to sign in</button></AuthLayout>
}

export default function App() {
  const path = usePath(), [user, setUser] = useState<UserProfile>(), [checked, setChecked] = useState(false)
  useEffect(() => { let active = true; void api.me().then(profile => active && setUser(profile)).catch(() => api.refresh().then(result => active && setUser(result.user)).catch(() => undefined)).finally(() => active && setChecked(true)); return () => { active = false } }, [])
  if (!checked) return <main className="loading-page">Loading AffectLab…</main>
  if (path.startsWith('/verify-email')) return <VerifyEmail/>
  if (path.startsWith('/reset-password')) return <ResetPassword/>
  if (path === '/forgot-password') return <ForgotPassword/>
  if (path.startsWith('/check-email')) return <CheckEmail/>
  if (path === '/signup') return <Signup/>
  if (path === '/login') return <Login onAuth={setUser}/>
  if (path === '/about') return <About user={user}/>
  const onboarding = user && !user.onboarding_completed ? <Onboarding user={user} onComplete={updated => { setUser(updated); navigate('/app') }} onSignOut={() => { setUser(undefined); navigate('/login') }}/> : null
  const practice = (profile:UserProfile) => { const query=new URLSearchParams(location.search);return <Dashboard user={profile} initialSessionId={query.get('session')??undefined} initialRoleplay={query.get('mode')==='roleplay'} onLogout={() => { setUser(undefined); navigate('/') }} onDashboard={() => navigate('/app')} onSettings={() => navigate('/settings')}/> }
  if (path === '/onboarding') return user ? (onboarding ?? <HomeDashboard user={user} onPractice={(id,roleplay)=>navigate(`/practice?${id?`session=${id}`:roleplay?'mode=roleplay':'new=1'}`)} onSettings={()=>navigate('/settings')} onHome={()=>navigate('/')} onLogout={()=>{setUser(undefined);navigate('/')}}/>) : <Login onAuth={setUser}/>
  if (path === '/settings') return user ? (onboarding ?? <SettingsPage user={user} onUser={setUser} onBack={() => navigate('/app')} onSignedOut={() => { setUser(undefined); navigate('/login') }}/>) : <Login onAuth={setUser}/>
  if (path.startsWith('/practice')) return user ? (onboarding ?? practice(user)) : <Login onAuth={setUser}/>
  if (path === '/app') return user ? (onboarding ?? <HomeDashboard user={user} onPractice={(id,roleplay)=>navigate(`/practice?${id?`session=${id}`:roleplay?'mode=roleplay':'new=1'}`)} onSettings={()=>navigate('/settings')} onHome={()=>navigate('/')} onLogout={()=>{setUser(undefined);navigate('/')}}/>) : <Login onAuth={setUser}/>
  return <Landing user={user}/>
}
