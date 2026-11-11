const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
localStorage.removeItem('meet-again-session');

export async function api(path, options = {}) {
  const { quietAuth = false, ...requestOptions } = options;
  const response = await fetch(base + path, { ...requestOptions, credentials: 'include', headers: { 'Content-Type': 'application/json', ...requestOptions.headers } });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = new Error(typeof data.detail === 'string' ? data.detail : data.detail?.[0]?.msg || `요청에 실패했습니다 (${response.status})`);
    error.status = response.status;
    if (response.status === 401 && !quietAuth) window.dispatchEvent(new Event('meet-again-auth-required'));
    throw error;
  }
  return response.status === 204 ? null : response.json();
}
export const post = (path, body, options = {}) => api(path, { ...options, method: 'POST', body: JSON.stringify(body) });
export async function currentUser() {
  try { return (await api('/auth/me', { quietAuth: true })).user; }
  catch (error) { if (error.status === 401) return null; throw error; }
}
