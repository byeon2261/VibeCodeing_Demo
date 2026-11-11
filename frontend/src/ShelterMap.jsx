import React, { useEffect, useRef, useState } from 'react';
import { ExternalLink, LoaderCircle, MapPin, RefreshCw } from 'lucide-react';
import { api } from './api';
import { loadKakaoMaps } from './kakaoMaps';

const mapKey = import.meta.env.VITE_KAKAO_JS_KEY;
const validCoordinates = location => {
  const { lat, lng } = location?.coordinates || {};
  return Number.isFinite(lat) && Number.isFinite(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
};

export default function ShelterMap({ candidate, runId }) {
  const container = useRef(null);
  const [location, setLocation] = useState(null);
  const [locationStatus, setLocationStatus] = useState('loading');
  const [mapStatus, setMapStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [attempt, setAttempt] = useState(0);
  const address = (candidate.shelter_address || '').trim();

  useEffect(() => {
    const controller = new AbortController();
    setLocation(null);
    setMapStatus('idle');
    setMessage('');
    if (candidate.sample || !address || address === 'None') {
      setLocationStatus('unavailable');
      setMessage(candidate.sample ? '샘플 공고의 보호센터 위치는 지도에 표시하지 않습니다.' : '공고에 보호센터 주소가 등록되어 있지 않습니다.');
      return () => controller.abort();
    }
    setLocationStatus('loading');
    const path = `/runs/${encodeURIComponent(runId)}/candidates/${encodeURIComponent(candidate.id)}/location`;
    api(path, { signal: controller.signal }).then(next => {
      if (controller.signal.aborted) return;
      setLocation(next);
      setLocationStatus(validCoordinates(next) ? 'ready' : 'unavailable');
      if (!validCoordinates(next)) setMessage(next.reason || '보호센터 주소의 좌표를 확인하지 못했습니다.');
    }).catch(error => {
      if (controller.signal.aborted) return;
      setLocationStatus('error');
      setMessage(error.message);
    });
    return () => controller.abort();
  }, [candidate.id, candidate.sample, address, runId, attempt]);

  const coordinates = validCoordinates(location) ? location.coordinates : null;
  useEffect(() => {
    if (!coordinates) return;
    if (!mapKey) {
      setMapStatus('unavailable');
      setMessage('지도를 표시할 수 없습니다. 아래 주소 링크로 보호센터 위치를 확인해 주세요.');
      return;
    }
    const element = container.current;
    let cancelled = false;
    let marker;
    let resizeObserver;
    setMapStatus('loading');
    loadKakaoMaps(mapKey).then(maps => {
      if (cancelled || !element) return;
      const center = new maps.LatLng(coordinates.lat, coordinates.lng);
      const map = new maps.Map(element, { center, level: 4 });
      marker = new maps.Marker({ map, position: center, title: candidate.shelter_name || '보호센터' });
      map.addControl(new maps.ZoomControl(), maps.ControlPosition.RIGHT);
      if (typeof ResizeObserver !== 'undefined') {
        resizeObserver = new ResizeObserver(() => { map.relayout(); map.setCenter(center); });
        resizeObserver.observe(element);
      }
      setMapStatus('ready');
    }).catch(error => {
      if (cancelled) return;
      setMapStatus('error');
      setMessage(error.message);
    });
    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      marker?.setMap(null);
      element?.replaceChildren();
    };
  }, [coordinates?.lat, coordinates?.lng, candidate.shelter_name, attempt]);

  const loading = locationStatus === 'loading' || (locationStatus === 'ready' && ['idle', 'loading'].includes(mapStatus));
  const ready = mapStatus === 'ready' && locationStatus === 'ready';
  const retry = locationStatus === 'error' || (locationStatus === 'ready' && mapStatus === 'error');
  const mapUrl = coordinates
    ? `https://map.kakao.com/link/map/${encodeURIComponent(candidate.shelter_name || '보호센터')},${coordinates.lat},${coordinates.lng}`
    : `https://map.kakao.com/link/search/${encodeURIComponent(address)}`;

  return <div className="shelter-location">
    <p className="shelter-address"><MapPin size={16}/><span>{address && address !== 'None' ? address : '보호센터 주소 미등록'}</span></p>
    <div className="shelter-map-frame" aria-busy={loading}>
      <div ref={container} className="map shelter-map-canvas" role="region" aria-label={`${candidate.shelter_name || '보호센터'} 위치 지도`} aria-hidden={!ready}/>
      {!ready && <div className="shelter-map-status" role={retry ? 'alert' : 'status'}>
        {loading ? <LoaderCircle size={24} className="spin"/> : <MapPin size={26}/>}
        <span>{loading ? locationStatus === 'loading' ? '보호센터 위치를 확인하고 있습니다…' : '카카오 지도를 불러오고 있습니다…' : message}</span>
        {retry && <button type="button" className="secondary" onClick={() => setAttempt(value => value + 1)}><RefreshCw size={14}/>지도 다시 불러오기</button>}
      </div>}
    </div>
    {ready && <p className="muted">보호센터 주소를 좌표로 변환한 위치입니다. 실제 방문 전 센터에 확인해 주세요.{location.fetched_at && <> · 위치 조회 {new Date(location.fetched_at).toLocaleString('ko-KR')}</>}</p>}
    {!candidate.sample && address && address !== 'None' && <a className="secondary" href={mapUrl} target="_blank" rel="noreferrer"><ExternalLink size={15}/>{coordinates ? '카카오맵에서 보호센터 보기' : '카카오맵에서 주소 검색'}</a>}
  </div>;
}
