
import React from 'react';

export const JsonCard: React.FC<{title?: string; data: any}> = ({title, data}) => {
  const text = React.useMemo(() => {
    try { return JSON.stringify(data, null, 2); } catch { return String(data); }
  }, [data]);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); alert('복사됨'); } catch { /* ignore */ }
  };
  return (
    <div style={{background:'#0b1220', color:'#cfe3ff', padding:'12px', borderRadius:8, border:'1px solid #1f2a44', fontSize:12}}>
      {title && <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
        <strong>{title}</strong>
        <button onClick={copy} style={{padding:'4px 8px', border:'1px solid #334', background:'#141b2d', color:'#cfe3ff', borderRadius:4, cursor:'pointer'}}>복사</button>
      </div>}
      <pre style={{margin:0, overflowX:'auto'}}>{text}</pre>
    </div>
  );
};
