// The SDK belongs to the page, so closing one popup must not remove it.
let pendingSdk;

export function loadKakaoMaps(key) {
  if (!key) return Promise.reject(new Error('지도 연결이 준비되지 않았습니다. 주소 링크로 위치를 확인해 주세요.'));
  if (window.kakao?.maps?.Map) return Promise.resolve(window.kakao.maps);
  if (pendingSdk) return pendingSdk;

  pendingSdk = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    let finished = false;
    const timer = setTimeout(() => fail(), 15000);
    const clean = () => {
      clearTimeout(timer);
      script.onload = null;
      script.onerror = null;
    };
    function fail() {
      if (finished) return;
      finished = true;
      clean();
      script.remove();
      pendingSdk = undefined;
      reject(new Error('카카오 지도를 불러오지 못했습니다. 다시 시도하거나 주소 링크로 위치를 확인해 주세요.'));
    }
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(key)}&autoload=false`;
    script.onerror = fail;
    script.onload = () => {
      if (finished) return;
      if (!window.kakao?.maps?.load) { fail(); return; }
      try {
        window.kakao.maps.load(() => {
          if (finished) return;
          if (!window.kakao?.maps?.Map) { fail(); return; }
          finished = true;
          clean();
          resolve(window.kakao.maps);
        });
      } catch { fail(); }
    };
    document.head.appendChild(script);
  });
  return pendingSdk;
}
