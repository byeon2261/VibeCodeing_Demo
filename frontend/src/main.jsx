import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { PawPrint, Search, Bookmark, Bell, Activity, ArrowRight, MapPin, Phone, X, Check, ChevronRight, RefreshCw, SlidersHorizontal, ShieldCheck, ExternalLink, Heart, LoaderCircle } from 'lucide-react';
import { api, post } from './api';
import './style.css';

function localDate(offset = 0) {
  const d = new Date(); d.setDate(d.getDate() + offset);
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul' }).format(d);
}
const empty = () => ({ region: '', species: '', start_date: localDate(-14), end_date: localDate(), breed: '', color: '', features: '' });
const names = { dog: '강아지', cat: '고양이', other: '기타 동물', all: '전체' };
const statuses = { completed: '검색 완료', partial: '일부 결과', failed: '확인 필요', awaiting_input: '추가 입력 필요' };

function MapView({ candidate }) {
  const ref = useRef(null);
  const [error, setError] = useState('');
  const coordinates = candidate.location?.coordinates;
  useEffect(() => {
    const key = import.meta.env.VITE_KAKAO_JS_KEY;
    if (!key || !coordinates) return;
    let cancelled = false;
    const initialize = () => window.kakao.maps.load(() => {
      if (cancelled || !ref.current) return;
      const center = new window.kakao.maps.LatLng(coordinates.lat, coordinates.lng);
      const map = new window.kakao.maps.Map(ref.current, { center, level: 4 });
      new window.kakao.maps.Marker({ map, position: center });
    });
    let script;
    if (window.kakao?.maps) initialize();
    else {
      script = document.createElement('script');
      script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(key)}&autoload=false`;
      script.onload = initialize;
      script.onerror = () => setError('카카오맵을 불러오지 못했습니다.');
      document.head.appendChild(script);
    }
    return () => { cancelled = true; if (script) script.remove(); };
  }, [coordinates?.lat, coordinates?.lng]);
  if (!coordinates || !import.meta.env.VITE_KAKAO_JS_KEY) return <div className="map-empty"><MapPin size={28}/><span>보호센터 위치</span><small>{candidate.shelter_address || '등록된 주소가 없습니다.'}</small></div>;
  return <><div ref={ref} className="map"/>{error && <p role="alert">{error}</p>}</>;
}

function App() {
  const [tab, setTab] = useState('search');
  const [form, setForm] = useState(empty);
  const [regions, setRegions] = useState([]);
  const [health, setHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [reflection, setReflection] = useState(true);
  const [useMemory, setUseMemory] = useState(false);
  const [selected, setSelected] = useState(null);
  const [saved, setSaved] = useState([]);
  const [runs, setRuns] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [recipient, setRecipient] = useState('');
  const [consent, setConsent] = useState(false);
  const [savedId, setSavedId] = useState('');
  const [name, setName] = useState('가족 찾기');
  const [includeLocation, setIncludeLocation] = useState(true);

  useEffect(() => {
    Promise.all([api('/health'), api('/regions')]).then(([h, r]) => { setHealth(h); setRegions(r); }).catch(() => setError('서버에 연결하지 못했습니다. 백엔드가 실행 중인지 확인해 주세요.'));
  }, []);
  useEffect(() => { if (!toast) return; const id = setTimeout(() => setToast(''), 4000); return () => clearTimeout(id); }, [toast]);
  useEffect(() => {
    if (!selected) return;
    const handler = e => { if (e.key === 'Escape') setSelected(null); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selected]);
  const cleaned = () => Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''));
  async function action(fn) {
    setError(''); setBusy(true);
    try { await fn(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function loadTab(next) {
    setTab(next); setError('');
    try {
      if (next === 'saved' || next === 'alerts') setSaved(await api('/saved-searches'));
      if (next === 'history') setRuns(await api('/runs'));
      if (next === 'alerts') { setSubscriptions(await api('/subscriptions')); setNotifications(await api('/notifications')); }
    } catch (e) { setError(e.message); }
  }
  const submit = e => {
    e.preventDefault();
    action(async () => {
      const data = await post('/searches', { conditions: cleaned(), reflection, use_memory: useMemory, include_location: includeLocation, ...(result?.status === 'awaiting_input' ? { thread_id: result.thread_id } : {}) });
      setResult(data);
      if (data.status === 'awaiting_input') setError(data.questions.join(' '));
    });
  };
  const save = () => action(async () => {
    const data = await post('/saved-searches', { name, conditions: result?.conditions || cleaned() });
    setSavedId(data.id); setToast('검색 조건을 저장했습니다.');
  });

  return <div className="app">
    <aside className="sidebar">
      <a href="#" className="brand" onClick={e => { e.preventDefault(); loadTab('search'); }}><span className="brand-icon"><PawPrint size={24}/></span><div>다시 만나<small>MEET AGAIN</small></div></a>
      <div className="side-label">우리 가족 찾기</div>
      <nav aria-label="주 메뉴">{[['search', Search, '구조동물 검색'], ['saved', Bookmark, '저장한 검색'], ['alerts', Bell, '알림 신청'], ['history', Activity, '실행 이력']].map(([id, Icon, label]) => <button key={id} className={tab === id ? 'nav active' : 'nav'} onClick={() => loadTab(id)}><Icon size={19}/>{label}{tab === id && <ChevronRight size={16}/>}</button>)}</nav>
      <div className="side-note"><Heart size={20}/><strong>작은 단서가<br/>다시 만나는 시작이 되도록.</strong><p>확인할 수 있는 정보를 모아<br/>가족을 찾는 길을 돕습니다.</p></div>
      <div className="side-bottom"><span className="dot"/> 로그인 없는 데모<small>이 브라우저에 연결된 검색을 보관해요.</small></div>
    </aside>

    <main>
      <header className="topbar"><span>다시 만나 <ChevronRight size={14}/> { {search:'구조동물 검색',saved:'저장한 검색',alerts:'알림 신청',history:'실행 이력'}[tab] }</span><span className="badge">{health ? health.mode === 'local' ? '샘플 데이터 모드' : '실제 API 모드' : '서버 확인 중'}</span></header>
      <div className="content">
        <div className="page-heading"><div className="eyebrow"><span/> 함께 찾는 소중한 가족</div><h1>{tab === 'search' ? <>다시 만날 수 있도록,<br/>작은 단서부터 찾아봐요.</> : tab === 'saved' ? '기억해 둔 검색 조건' : tab === 'alerts' ? '새로운 단서를 전해드려요.' : '검색이 걸어온 길'}</h1><p>{tab === 'search' ? '구조·보호 중인 동물 공고에서 우리 가족과 닮은 후보를 확인하세요.' : tab === 'saved' ? '저장해 둔 조건으로 다시 검색하거나 알림을 신청할 수 있어요.' : tab === 'alerts' ? '신청 후 직접 실행한 검색에서 조건에 맞는 후보를 찾으면 Discord DM으로 알려드려요.' : '도구 선택부터 검증과 수정까지, 실행 결과를 확인할 수 있어요.'}</p></div>
        {health?.mode === 'local' && <div className="notice"><ShieldCheck size={18}/><span>지금은 <b>생성된 샘플 데이터</b>를 사용합니다. 실제 동물·보호센터 공고가 아니며 알림을 발송하지 않습니다.</span></div>}
        {error && <div className="error" role="alert">{error}<button aria-label="오류 닫기" onClick={() => setError('')}><X size={16}/></button></div>}

        {tab === 'search' && <>
          <section className="panel search-panel"><div className="section-heading"><h2><SlidersHorizontal size={19}/> 어떤 가족을 찾고 계신가요?</h2><span>* 필수 조건</span></div>
            <form onSubmit={submit}>
              <div className="species" role="group" aria-label="동물 종류">{Object.entries(names).map(([value, label]) => <button type="button" key={value} className={form.species === value ? 'chosen' : ''} onClick={() => setForm({ ...form, species: value })}><PawPrint size={17}/>{label}{form.species === value && <Check size={15}/>}</button>)}</div>
              <div className="form-grid"><label>검색 지역 *<select value={form.region} onChange={e => setForm({ ...form, region: e.target.value })}><option value="">시도 선택</option>{regions.map(r => <option key={r.code}>{r.name}</option>)}</select></label><label>검색 시작일 *<input type="date" max={localDate()} value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })}/></label><label>검색 종료일 *<input type="date" max={localDate()} value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })}/></label></div>
              <div className="form-grid"><label>품종 <em>선택</em><input placeholder="예: 푸들, 한국 고양이" value={form.breed} maxLength={80} onChange={e => setForm({ ...form, breed: e.target.value })}/></label><label>털색 <em>선택</em><input placeholder="예: 갈색, 흰색" value={form.color} maxLength={80} onChange={e => setForm({ ...form, color: e.target.value })}/></label><label>기억할 특징 <em>선택</em><input placeholder="예: 빨간 목줄, 귀 끝 흰 털" value={form.features} maxLength={500} onChange={e => setForm({ ...form, features: e.target.value })}/></label></div>
              <div className="form-footer"><div className="toggles"><label><input type="checkbox" checked={reflection} onChange={e => setReflection(e.target.checked)}/> 자가 성찰 적용</label><label><input type="checkbox" checked={useMemory} onChange={e => setUseMemory(e.target.checked)}/> 저장한 특징 사용</label><label><input type="checkbox" checked={includeLocation} onChange={e => setIncludeLocation(e.target.checked)}/> 보호센터 위치 확인</label></div><button className="primary" disabled={busy}>{busy ? <LoaderCircle size={18} className="spin"/> : <Search size={18}/>} {busy ? '단서를 확인하는 중…' : '구조동물 찾기'}</button></div>
            </form>
          </section>
          {result ? <section className="results"><div className="results-heading"><h2>확인할 유사 후보 <span>{result.candidates.length}</span></h2><span className="muted">{statuses[result.status]} · {result.elapsed_ms ?? 0}ms</span></div><p className="muted">{result.coverage?.total ?? 0}건 중 최대 상위 10건 표시 · 조회 {result.coverage?.pages ?? 0}페이지{result.coverage?.partial ? ' · 전체 검색이 아닌 일부 범위입니다.' : ''}</p>{result.coverage?.fetched_at && <p className="muted">조회 시각 {new Date(result.coverage.fetched_at).toLocaleString('ko-KR')} · {result.coverage.source}</p>}
            {result.errors?.map((item, i) => <p className="error" key={i}>{item.message}</p>)}
            <div className="cards">{result.candidates.map(c => <button className="animal-card" key={c.id} onClick={() => setSelected(c)}><div className="animal-image">{c.image_url ? <img loading="lazy" src={c.image_url} alt={c.breed || '구조동물 사진'} onError={e => { e.currentTarget.style.display = 'none'; }}/>: <><PawPrint size={48} strokeWidth={1.1}/><small>{c.sample ? 'SAMPLE · 가상 동물' : '등록된 사진 없음'}</small></>}<span className="image-tag">{c.sample ? '샘플' : c.status || '상태 미확인'}</span></div><div className="animal-body"><div className="animal-title"><h3>{c.breed || names[c.species]}</h3><ArrowRight size={18}/></div><p>{c.color || '털색 미상'} · {c.found_date}</p><p><MapPin size={14}/>{c.found_place || '구조 위치 미상'}</p><div className="match"><span>{c.matches.length ? '일치 단서 ' + c.matches.length + '개' : '특징을 추가해 비교해 보세요'}</span><b>{c.score}점</b></div></div></button>)}</div>
            {!result.candidates.length && <div className="empty"><Search size={32}/><h3>{result.status === 'awaiting_input' ? '필요한 조건을 더 알려주세요.' : result.status === 'failed' ? '검색을 완료하지 못했어요.' : '조회 범위에서 후보를 찾지 못했어요.'}</h3><p>입력 조건과 오류 안내를 확인해 주세요. 빈 결과가 동물이 보호 중이지 않다는 뜻은 아닙니다.</p></div>}
            <div className="save-row"><input aria-label="저장 검색 이름" value={name} maxLength={80} onChange={e => setName(e.target.value)}/><button className="secondary" disabled={busy || !['completed', 'partial'].includes(result.status)} onClick={save}><Bookmark size={16}/> 조건 저장</button><button className="secondary" disabled={busy} onClick={() => action(async () => { await api('/memory', { method: 'PUT', body: JSON.stringify({ confirmed: true, conditions: cleaned() }) }); setToast('입력한 동물 특징을 확인된 기억으로 저장했습니다.'); })}>입력 특징을 확인하고 기억</button></div>
            <details className="panel trace"><summary>이번 검색의 검증·수정 이력 <span>{result.iteration}회 수정 · {result.tool_calls}회 도구 호출 · {result.tokens} 토큰</span></summary>{result.traces.map((t, i) => <div className="trace-row" key={i}><span>{i + 1}</span><b>{t.node}</b><p>{t.detail}</p></div>)}</details>
          </section> : <div className="intro-grid"><div><span className="step">01</span><h3>기억나는 단서를 입력해요</h3><p>지역과 기간, 동물 종류를 먼저 선택하고<br/>품종이나 특징을 더해 주세요.</p></div><div><span className="step">02</span><h3>닮은 후보를 살펴봐요</h3><p>일치하는 특징과 확인이 필요한 정보를<br/>함께 비교할 수 있어요.</p></div><div><span className="step">03</span><h3>보호센터에 확인해요</h3><p>사진과 공고를 확인한 뒤<br/>보호센터에 직접 문의해 주세요.</p></div></div>}
        </>}

        {tab === 'saved' && <section className="panel"><div className="section-heading"><h2>저장한 검색</h2><button className="text-button" onClick={() => loadTab('saved')}><RefreshCw size={16}/> 새로고침</button></div>{saved.length ? saved.map(s => <div className="list-row" key={s.id}><Bookmark size={21}/><div><h3>{s.name}</h3><p>{s.conditions.region} · {names[s.conditions.species]} · {s.conditions.start_date} ~ {s.conditions.end_date}</p></div><button className="secondary" onClick={() => { setForm({ ...empty(), ...s.conditions }); setResult(null); setTab('search'); }}>불러오기</button><button className="text-button" onClick={() => { setSavedId(s.id); loadTab('alerts'); }}>알림 신청</button><button className="icon-button" aria-label={`${s.name} 삭제`} onClick={() => action(async () => { await api('/saved-searches/' + s.id, { method: 'DELETE' }); await loadTab('saved'); })}><X size={18}/></button></div>) : <div className="empty"><Bookmark/><h3>아직 저장한 검색이 없어요.</h3><p>검색을 완료한 뒤 조건을 저장해 보세요.</p></div>}<button className="text-button" disabled={busy} onClick={() => action(async () => { await api('/memory/default', { method: 'DELETE' }); setToast('저장한 동물 특징을 삭제했습니다.'); })}>저장한 동물 특징 삭제</button></section>}

        {tab === 'alerts' && <div className="alert-grid"><section className="panel"><h2><Bell size={20}/> Discord DM 알림 신청</h2><p className="muted">자동·주기적 검색은 하지 않습니다. 이 브라우저에서 직접 검색한 결과를 저장 조건과 대조해 발송합니다. 샘플 모드에서는 실제 발송하지 않습니다.</p><form onSubmit={e => { e.preventDefault(); action(async () => { await post('/subscriptions', { saved_search_id: savedId, recipient, consent, channel: 'discord' }); setToast('알림 신청을 등록했습니다.'); await loadTab('alerts'); }); }}><label>저장한 검색<select value={savedId} onChange={e => setSavedId(e.target.value)} required><option value="">검색 조건 선택</option>{saved.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label>Discord 사용자 ID<input placeholder="서버 허용 목록에 등록한 사용자 ID" value={recipient} onChange={e => setRecipient(e.target.value)} pattern="[0-9]{17,20}" required/></label><label className="check-label"><input type="checkbox" checked={consent} required onChange={e => setConsent(e.target.checked)}/> 선택한 조건의 후보 알림 수신에 동의합니다.</label><button className="primary" disabled={busy || !health?.discord_configured}><Bell size={17}/> 알림 신청</button>{!health?.discord_configured && <p className="muted">서버의 Discord Bot과 수신자 허용 목록 설정이 필요합니다.</p>}<p className="muted">문자·브라우저 푸시는 이번 구현에 포함되지 않습니다.</p></form></section><section className="panel"><h2>신청·발송 이력</h2>{subscriptions.map(s => <div className="list-row" key={s.id}><div><b>Discord DM · 신청 중</b><p>{saved.find(x => x.id === s.saved_search_id)?.name || '저장 검색'}</p></div><button className="text-button" onClick={() => action(async () => { await api('/subscriptions/' + s.id, { method: 'DELETE' }); await loadTab('alerts'); })}>해제</button></div>)}{notifications.map(n => <div className="list-row" key={n.id}><div><b>{n.candidate_id}</b><p>{n.status === 'accepted' ? 'Discord 요청 수락 (수신 확인 필요)' : n.status === 'pending' ? '발송 중 또는 확인 필요' : '발송 실패 또는 수락 확인 불가'}</p>{n.error && <p>{n.error}</p>}</div></div>)}{!subscriptions.length && !notifications.length && <div className="empty"><Bell/><p>등록된 알림이 없습니다.</p></div>}</section></div>}

        {tab === 'history' && <section className="panel"><div className="section-heading"><h2>최근 실행</h2><button className="text-button" onClick={() => loadTab('history')}><RefreshCw size={16}/> 새로고침</button></div>{runs.map(r => <details className="history" key={r.id}><summary><span className="badge">{statuses[r.status]}</span> {r.conditions.region || '지역 미입력'} · {names[r.conditions.species] || '종류 미입력'}<small>{r.reflection ? '성찰 ON' : '성찰 OFF'} · {r.iteration}회 수정 · {r.elapsed_ms ?? 0}ms</small></summary>{r.traces.map((t, i) => <div className="trace-row" key={i}><b>{t.node}</b><p>{t.detail}</p></div>)}</details>)}{!runs.length && <div className="empty"><Activity/><p>첫 검색을 실행해 보세요.</p></div>}</section>}
        <footer><PawPrint size={15}/><span>다시 만나 · 후보의 유사도는 동일 동물일 확률이 아닙니다. 최종 확인은 보호센터에 문의해 주세요.</span></footer>
      </div>
    </main>
    {toast && <div className="toast" role="status"><Check size={18}/>{toast}</div>}
    {selected && <div className="modal-backdrop" onClick={() => setSelected(null)}><section className="modal" role="dialog" aria-modal="true" aria-label="공고 상세" onClick={e => e.stopPropagation()}><button autoFocus className="modal-close" aria-label="상세 닫기" onClick={() => setSelected(null)}><X/></button><span className="eyebrow">{selected.sample ? '가상 샘플 공고' : selected.notice_no}</span><h2>{selected.breed}</h2><p>{selected.features || '등록된 특징 없음'}</p>{selected.image_url && <img className="detail-image" src={selected.image_url} alt={selected.breed}/>}<div className="detail-grid"><div><small>발견 일자</small><b>{selected.found_date}</b></div><div><small>공고 상태</small><b>{selected.status || '정보 없음'}</b></div></div><h3>비교한 단서 · {selected.score}점</h3>{selected.matches.map((x,i) => <p className="green" key={i}>일치 · {x}</p>)}{selected.mismatches.map((x,i) => <p key={i}>불일치/부분 일치 · {x}</p>)}{selected.unknown.map((x,i) => <p className="muted" key={i}>미확인 · {x}</p>)}<p className="muted">단순 문자열·가중치 점수이며 동일 개체의 확률이 아닙니다.</p><h3>구조 위치</h3><p>{selected.found_place || '위치 정보 없음'}</p>{!selected.sample && selected.found_place && <a className="text-button" target="_blank" rel="noreferrer" href={`https://map.kakao.com/link/search/${encodeURIComponent(selected.found_place)}`}>카카오맵에서 구조 장소 검색 <ExternalLink size={14}/></a>}<h3>보호센터 · {selected.shelter_name || '미상'}</h3><MapView candidate={selected}/>{selected.shelter_phone && <a className="primary" href={`tel:${selected.shelter_phone.replace(/[^0-9+]/g, '')}`}><Phone size={16}/>{selected.shelter_phone}</a>}{!selected.sample && selected.shelter_address && <a className="secondary" href={selected.location?.map_url || `https://map.kakao.com/link/search/${encodeURIComponent(selected.shelter_address)}`} target="_blank" rel="noreferrer"><MapPin size={16}/>보호센터 위치 확인</a>}<p className="muted">조회 시각 {new Date(selected.fetched_at).toLocaleString('ko-KR')}</p><a href={selected.source_url} target="_blank" rel="noreferrer" className="text-button">공식 출처 확인 <ExternalLink size={14}/></a></section></div>}
  </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
