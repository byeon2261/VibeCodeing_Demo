const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
let token = localStorage.getItem('meet-again-session');
let sessionPromise;

export async function api(path, options = {}, retry = true) {
  if (!token && path !== '/sessions' && path !== '/health' && path !== '/regions') {
    if (!sessionPromise) sessionPromise = fetch(base + '/sessions', { method: 'POST' }).then(async response => {
      if (!response.ok) throw new Error('데모 세션 생성에 실패했습니다. 백엔드 연결을 확인해 주세요.');
      token = (await response.json()).token;
      localStorage.setItem('meet-again-session', token);
    }).finally(() => { sessionPromise = null; });
    await sessionPromise;
  }
  const response = await fetch(base + path, { ...options, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers } });
  if (response.status === 401 && retry) {
    token = null;
    localStorage.removeItem('meet-again-session');
    return api(path, options, false);
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.[0]?.msg || `요청에 실패했습니다 (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}
export const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body) });
