import React, { useState } from 'react';
import { PawPrint, ArrowLeft, ArrowRight, Eye, EyeOff, Heart, Bookmark, ShieldCheck, LoaderCircle } from 'lucide-react';
import { post } from './api';

export default function AuthPage({ onAuthenticated, navigate }) {
  const [register, setRegister] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', name: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const body = { email: form.email.trim(), password: form.password, ...(register ? { name: form.name.trim() } : {}) };
      const data = await post(register ? '/auth/register' : '/auth/login', body, { quietAuth: true });
      onAuthenticated(data.user);
    } catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  return <main className="auth-page">
    <a className="auth-back" href="/" onClick={e => { e.preventDefault(); navigate('/'); }}><ArrowLeft size={17}/> 검색 화면으로 돌아가기</a>
    <div className="auth-shell">
      <section className="auth-story">
        <a className="brand" href="/" onClick={e => { e.preventDefault(); navigate('/'); }}><span className="brand-icon"><PawPrint size={25}/></span><div>다시 만나<small>MEET AGAIN</small></div></a>
        <div className="auth-story-copy"><span className="eyebrow">다시 만날 수 있다는 믿음</span><h1>소중한 가족을 찾는 길,<br/>함께 이어가요.</h1><p>기억해 둔 작은 단서들이<br/>다시 만나는 순간으로 이어지도록.</p></div>
        <div className="auth-benefits"><div><Bookmark size={20}/><span><b>단서를 차곡차곡</b><small>저장한 검색을 언제든 다시 확인해요.</small></span></div><div><Heart size={20}/><span><b>이어지는 찾기의 기록</b><small>기기와 브라우저가 달라도 함께해요.</small></span></div><div><ShieldCheck size={20}/><span><b>나만의 공간</b><small>검색 기록을 내 계정에 안전하게 보관해요.</small></span></div></div>
        <PawPrint className="auth-watermark" aria-hidden="true"/>
      </section>
      <section className="auth-form-panel">
        <span className="eyebrow">MEET AGAIN</span><h2>{register ? '함께 찾기를 시작해요' : '다시 만나서 반가워요'}</h2><p className="auth-description">{register ? '계정을 만들고 소중한 단서를 보관하세요.' : '로그인하고 가족을 찾는 여정을 이어가세요.'}</p>
        <div className="auth-tabs" role="group" aria-label="계정 메뉴"><button type="button" disabled={busy} className={!register ? 'active' : ''} onClick={() => { setRegister(false); setError(''); }}>로그인</button><button type="button" disabled={busy} className={register ? 'active' : ''} onClick={() => { setRegister(true); setError(''); }}>회원가입</button></div>
        <form onSubmit={submit}>
          {register && <label htmlFor="auth-name">이름<input id="auth-name" autoComplete="name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="어떻게 불러드릴까요?" required minLength={1} maxLength={40} disabled={busy}/></label>}
          <label htmlFor="auth-email">이메일<input id="auth-email" type="email" autoComplete="username" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="name@example.com" required maxLength={254} disabled={busy}/></label>
          <label htmlFor="auth-password">비밀번호<span className="password-field"><input id="auth-password" type={showPassword ? 'text' : 'password'} autoComplete={register ? 'new-password' : 'current-password'} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder={register ? '10자 이상으로 입력해 주세요' : '비밀번호를 입력해 주세요'} required minLength={10} maxLength={128} disabled={busy}/><button type="button" aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}</button></span></label>
          {register && <p className="auth-password-hint">다른 서비스에서 사용하지 않는 비밀번호를 권장해요.</p>}
          {error && <div className="error" role="alert">{error}</div>}
          <button type="submit" className="primary auth-submit" disabled={busy}>{busy ? <LoaderCircle size={18} className="spin"/> : <>{register ? '계정 만들기' : '로그인'}<ArrowRight size={17}/></>}</button>
        </form>
        <p className="auth-switch">{register ? '이미 계정이 있으신가요?' : '아직 계정이 없으신가요?'} <button type="button" disabled={busy} onClick={() => { setRegister(!register); setError(''); }}>{register ? '로그인' : '회원가입'}</button></p>
        <div className="auth-form-footer"><PawPrint size={15}/><span>작은 단서가, 다시 만나는 시작이 되도록.</span></div>
      </section>
    </div>
  </main>;
}
