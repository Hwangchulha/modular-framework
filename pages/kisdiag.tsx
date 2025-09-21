
import React from 'react';
import { JsonCard } from '../components/JsonCard';

type Cfg = {
  appkey?: string;
  appsecret?: string;
  account_no?: string;
  product_code?: string;
  custtype?: string;
  env?: 'prod'|'vts'|string;
};

function guessApiBase(): string {
  if (typeof process !== 'undefined' && process.env && (process.env as any).NEXT_PUBLIC_API_BASE) {
    return (process.env as any).NEXT_PUBLIC_API_BASE as string;
  }
  if (typeof window !== 'undefined') {
    const loc = window.location;
    return `${loc.protocol}//${loc.hostname}:8000`;
  }
  return 'http://localhost:8000';
}

function getBearer(): Record<string,string> {
  if (typeof window === 'undefined') return {};
  const candidates = ['accessToken','token','jwt','id_token','auth'];
  for (const k of candidates) {
    const raw = window.localStorage.getItem(k);
    if (!raw) continue;
    try {
      const parsed = JSON.parse(raw);
      const val = parsed?.accessToken || parsed?.token || parsed;
      if (typeof val === 'string') return { 'Authorization': `Bearer ${val}` };
    } catch {
      return { 'Authorization': `Bearer ${raw}` };
    }
  }
  return {};
}

const Page: React.FC = () => {
  const [cfg, setCfg] = React.useState<Cfg>(() => {
    if (typeof window === 'undefined') return { env:'prod', product_code:'01', custtype:'P' };
    try {
      const saved = JSON.parse(window.localStorage.getItem('kis.cfg') || '{}');
      return { env:'prod', product_code:'01', custtype:'P', ...saved };
    } catch { return { env:'prod', product_code:'01', custtype:'P' }; }
  });
  const [api] = React.useState<string>(guessApiBase());
  const [checkRes, setCheckRes] = React.useState<any>(null);
  const [accountRes, setAccountRes] = React.useState<any>(null);
  const [matchRes, setMatchRes] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);
  const headers = React.useMemo(() => ({ 'Content-Type':'application/json', ...getBearer() }), []);

  const saveCfg = () => {
    if (typeof window !== 'undefined') window.localStorage.setItem('kis.cfg', JSON.stringify(cfg || {}));
    alert('설정 저장됨 (브라우저 로컬)');
  };

  const onChange = (k: keyof Cfg) => (e: any) => setCfg(v => ({...v, [k]: e.target.value}));

  const post = async (path: string) => {
    setBusy(true);
    try {
      const res = await fetch(`${api}${path}`, {method:'POST', headers, body: JSON.stringify(cfg)});
      const js = await res.json().catch(() => ({_raw: await res.text()}));
      js._http = {status: res.status};
      return js;
    } finally { setBusy(false); }
  };

  const doCheck = async () => setCheckRes(await post('/_kisdiag/check'));
  const doAccount = async () => setAccountRes(await post('/_kisdiag/account'));
  const doMatch = async () => setMatchRes(await post('/_kisdiag/account/match'));

  const card = (label: string, onClick: () => void) => (
    <button onClick={onClick} disabled={busy} style={{marginRight:8, padding:'8px 14px', border:'1px solid #334', background:'#141b2d', color:'#cfe3ff', borderRadius:6, cursor:'pointer'}}>
      {label}
    </button>
  );

  return (
    <div style={{maxWidth:980, margin:'24px auto', padding:'0 16px'}}>
      <h1 style={{marginBottom:6}}>KIS 진단 (GUI)</h1>
      <p style={{marginTop:0, color:'#5A6A85'}}>버튼만 눌러 실제 호출 상태를 확인해요. 실/모의는 <code>env</code>로 전환합니다.</p>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:12}}>
        <div>
          <label>env</label>
          <select value={cfg.env || 'prod'} onChange={onChange('env')} style={{width:'100%', padding:8}}>
            <option value="prod">prod (실계좌)</option>
            <option value="vts">vts (모의)</option>
          </select>
        </div>
        <div>
          <label>account_no (CANO 8자리)</label>
          <input value={cfg.account_no || ''} onChange={onChange('account_no')} placeholder="계좌번호 8자리" style={{width:'100%', padding:8}} />
        </div>
        <div>
          <label>product_code</label>
          <input value={cfg.product_code || '01'} onChange={onChange('product_code')} placeholder="01" style={{width:'100%', padding:8}} />
        </div>
        <div>
          <label>custtype</label>
          <input value={cfg.custtype || 'P'} onChange={onChange('custtype')} placeholder="P" style={{width:'100%', padding:8}} />
        </div>
        <div>
          <label>appkey</label>
          <input value={cfg.appkey || ''} onChange={onChange('appkey')} placeholder="App Key" style={{width:'100%', padding:8}} />
        </div>
        <div>
          <label>appsecret</label>
          <input value={cfg.appsecret || ''} onChange={onChange('appsecret')} placeholder="App Secret" style={{width:'100%', padding:8}} />
        </div>
      </div>

      <div style={{marginBottom:12}}>
        {card('연결 점검(check)', doCheck)}
        {card('잔고 원본 호출(account)', doAccount)}
        {card('UI 결과와 비교(match)', doMatch)}
        <button onClick={saveCfg} style={{marginLeft:8, padding:'8px 14px', border:'1px solid #334', background:'#0d2', color:'#081', borderRadius:6, cursor:'pointer'}}>입력 저장</button>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr', gap:12}}>
        {checkRes && <JsonCard title="check 결과" data={checkRes} />}
        {accountRes && <JsonCard title="account 결과" data={accountRes} />}
        {matchRes && <JsonCard title="match 결과 (diff 포함)" data={matchRes} />}
      </div>

      <div style={{marginTop:16, color:'#6b7c93', fontSize:12}}>
        <div>API base: <code>{api}</code></div>
        <div>※ 데이터/연동은 지연·오류 가능. 본 도구/결과는 투자권유가 아닙니다. API 약관 및 키/계좌 보안 준수.</div>
      </div>
    </div>
  );
};

export default Page;
