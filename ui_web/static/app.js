// Minimal SPA for login/signup/profile
const qs = (sel, el=document) => el.querySelector(sel);
const apiPort = 8000; // default API port
const uiPort = location.port || 8080;

// Compute API base (same host, apiPort)
const API_BASE = `${location.protocol}//${location.hostname}:${apiPort}`;
qs('#apiBase').textContent = API_BASE;

let accessToken = null;
let refreshToken = localStorage.getItem('mf_refresh') || null;

const state = { user: null };

function navTo(name){
  for(const b of document.querySelectorAll('nav button')){
    b.classList.toggle('active', b.dataset.nav === name);
  }
  if(name === 'login') renderLogin();
  if(name === 'signup') renderSignup();
  if(name === 'profile') renderProfile();
}

async function apiRun(moduleName, payload) {
  const res = await fetch(`${API_BASE}/run?name=${encodeURIComponent(moduleName)}`, {
    method: 'POST',
    headers: {
      'Content-Type':'application/json',
      ...(accessToken ? {'Authorization': 'Bearer ' + accessToken} : {})
    },
    body: JSON.stringify(payload)
  });
  return await res.json();
}

async function tryRefresh() {
  if(!refreshToken) return false;
  const out = await apiRun('modules.auth.login', {action:'REFRESH', mode:'SINGLE', input:{refresh_token: refreshToken}});
  if(out.ok){
    accessToken = out.data.access_token;
    return true;
  } else {
    localStorage.removeItem('mf_refresh');
    refreshToken = null;
    accessToken = null;
    return false;
  }
}

async function guardedRun(moduleName, payload){
  let out = await apiRun(moduleName, payload);
  if(!out.ok && out.error && out.error.code === 'ERR_FORBIDDEN'){
    // try refresh
    const ok = await tryRefresh();
    if(ok) out = await apiRun(moduleName, payload);
  }
  return out;
}

// ------- Views -------
function renderLogin(){
  const view = qs('#view');
  view.innerHTML = `
    <div class="card">
      <h2>로그인</h2>
      <label>이메일</label>
      <input id="lg_email" type="email" placeholder="you@example.com"/>
      <label>비밀번호</label>
      <input id="lg_pw" type="password" placeholder="••••••"/>
      <div><label><input id="lg_rem" type="checkbox"/> 자동 로그인(기기 저장)</label></div>
      <button class="primary" id="btn_login">로그인</button>
      <div class="note" id="lg_msg"></div>
    </div>
  `;
  qs('#btn_login').onclick = async () => {
    const email = qs('#lg_email').value.trim();
    const password = qs('#lg_pw').value;
    const remember_me = qs('#lg_rem').checked;
    const out = await apiRun('modules.auth.login', {action:'LOGIN', mode:'SINGLE', input:{email, password, remember_me}});
    if(out.ok){
      accessToken = out.data.access_token;
      refreshToken = out.data.refresh_token;
      if(remember_me) localStorage.setItem('mf_refresh', refreshToken);
      qs('#lg_msg').textContent = '로그인 성공';
      await loadWhoAmI();
      navTo('profile');
    }else{
      qs('#lg_msg').textContent = '로그인 실패: ' + (out.error?.message || '알 수 없는 오류');
    }
  };
}

function renderSignup(){
  const view = qs('#view');
  view.innerHTML = `
    <div class="card">
      <h2>회원가입</h2>
      <div class="row">
        <div>
          <label>이메일</label>
          <input id="su_email" type="email" placeholder="you@example.com"/>
        </div>
        <div>
          <label>닉네임</label>
          <input id="su_nick" type="text" placeholder="별명"/>
        </div>
      </div>
      <label>비밀번호</label>
      <input id="su_pw" type="password" placeholder="6자 이상"/>
      <button class="primary" id="btn_signup">가입하기</button>
      <div class="note" id="su_msg"></div>
    </div>
  `;
  qs('#btn_signup').onclick = async () => {
    const email = qs('#su_email').value.trim();
    const password = qs('#su_pw').value;
    const nickname = qs('#su_nick').value.trim();
    const out = await apiRun('modules.auth.users', {action:'REGISTER', mode:'SINGLE', input:{email, password, nickname}});
    if(out.ok){
      qs('#su_msg').textContent = '가입 완료! 로그인 탭에서 로그인하세요.';
    }else{
      qs('#su_msg').textContent = '가입 실패: ' + (out.error?.message || '알 수 없는 오류');
    }
  };
}

function renderProfile(){
  const view = qs('#view');
  view.innerHTML = `
    <div class="card">
      <h2>프로필</h2>
      <div id="pf_block" class="${state.user ? '' : 'hidden'}">
        <div class="row">
          <div>
            <label>이메일</label>
            <input id="pf_email" type="email" disabled/>
          </div>
          <div>
            <label>닉네임</label>
            <input id="pf_nick" type="text"/>
          </div>
        </div>
        <button class="primary" id="btn_save">저장</button>
        <button id="btn_logout">로그아웃</button>
      </div>
      <div id="pf_msg" class="note"></div>
    </div>

    <div class="card">
      <h3>내 토큰</h3>
      <pre id="pf_tokens"></pre>
    </div>
  `;
  updateProfileView();
  qs('#btn_save').onclick = async () => {
    const nickname = qs('#pf_nick').value.trim();
    const out = await guardedRun('modules.auth.users', {action:'UPDATE', mode:'SINGLE', input:{nickname}});
    if(out.ok){
      qs('#pf_msg').textContent = '저장 완료';
      await loadWhoAmI();
    }else{
      qs('#pf_msg').textContent = '저장 실패: ' + (out.error?.message || '오류');
    }
  };
  qs('#btn_logout').onclick = async () => {
    if(refreshToken){
      await apiRun('modules.auth.login', {action:'LOGOUT', mode:'SINGLE', input:{refresh_token: refreshToken}});
    }
    localStorage.removeItem('mf_refresh');
    accessToken = null; refreshToken = null; state.user = null;
    qs('#pf_tokens').textContent = '';
    renderLogin();
  };
}

function updateProfileView(){
  const user = state.user;
  const block = qs('#pf_block');
  if(!user){ block.classList.add('hidden'); qs('#pf_msg').textContent = '로그인이 필요합니다.'; return; }
  block.classList.remove('hidden');
  qs('#pf_email').value = user.email || '';
  qs('#pf_nick').value = user.nickname || '';
  qs('#pf_tokens').textContent = JSON.stringify({accessToken, refreshToken: !!refreshToken}, null, 2);
}

async function loadWhoAmI(){
  const out = await guardedRun('modules.auth.login', {action:'WHOAMI', mode:'SINGLE', input:{}});
  if(out.ok && out.data && out.data.id){
    state.user = out.data;
  }else{
    state.user = null;
  }
  if(qs('#pf_block')) updateProfileView();
}

// Auto-login on load
(async () => {
  if(refreshToken) await tryRefresh();
  await loadWhoAmI();
  navTo(state.user ? 'profile' : 'login');
})();

// Nav
for(const b of document.querySelectorAll('nav button')){
  b.addEventListener('click', () => navTo(b.dataset.nav));
}
