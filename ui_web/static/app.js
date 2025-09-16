// Minimal SPA for login/signup/profile + password reset
const qs = (sel, el=document) => el.querySelector(sel);
const apiPort = 8000;
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
  if(name === 'reset') renderReset();
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
    if(out.data.refresh_token){ // rotation
      refreshToken = out.data.refresh_token;
      localStorage.setItem('mf_refresh', refreshToken);
    }
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
      <h3>비밀번호 변경</h3>
      <label>현재 비밀번호</label>
      <input id="cp_old" type="password"/>
      <label>새 비밀번호</label>
      <input id="cp_new" type="password"/>
      <button class="primary" id="btn_cp">변경</button>
      <div class="note" id="cp_msg"></div>
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
    qs('#pf_msg').textContent = out.ok ? '저장 완료' : ('저장 실패: ' + (out.error?.message || '오류'));
    if(out.ok) await loadWhoAmI();
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
  qs('#btn_cp').onclick = async () => {
    const old_password = qs('#cp_old').value;
    const new_password = qs('#cp_new').value;
    const out = await guardedRun('modules.auth.users', {action:'CHANGE_PASSWORD', mode:'SINGLE', input:{old_password, new_password}});
    qs('#cp_msg').textContent = out.ok ? '변경 완료' : ('변경 실패: ' + (out.error?.message || '오류'));
  };
}

function renderReset(){
  const view = qs('#view');
  view.innerHTML = `
    <div class="card">
      <h2>비밀번호 재설정</h2>
      <label>이메일</label>
      <input id="rs_email" type="email" placeholder="you@example.com"/>
      <button class="primary" id="btn_req">재설정 코드 받기</button>
      <div class="note" id="rs_msg"></div>
    </div>
    <div class="card">
      <h3>코드 입력</h3>
      <label>코드</label>
      <input id="rs_code" type="text" placeholder="6자리 코드"/>
      <label>새 비밀번호</label>
      <input id="rs_new" type="password" placeholder="6자 이상"/>
      <button class="primary" id="btn_cfm">확정</button>
      <div class="note" id="rs_cfm_msg"></div>
    </div>
  `;
  qs('#btn_req').onclick = async () => {
    const email = qs('#rs_email').value.trim();
    const out = await apiRun('modules.auth.reset', {action:'REQUEST', mode:'SINGLE', input:{email}});
    if(out.ok){
      qs('#rs_msg').textContent = out.data.code ? `코드: ${out.data.code}` : '등록된 이메일이면 코드가 발송되었습니다.';
    }else{
      qs('#rs_msg').textContent = '요청 실패: ' + (out.error?.message || '오류');
    }
  };
  qs('#btn_cfm').onclick = async () => {
    const email = qs('#rs_email').value.trim();
    const code = qs('#rs_code').value.trim();
    const new_password = qs('#rs_new').value;
    const out = await apiRun('modules.auth.reset', {action:'CONFIRM', mode:'SINGLE', input:{email, code, new_password}});
    qs('#rs_cfm_msg').textContent = out.ok ? '재설정 완료! 로그인하세요.' : ('실패: ' + (out.error?.message || '오류'));
  };
}

function updateProfileView(){
  const user = state.user;
  const block = qs('#pf_block');
  if(!user){ block.classList.add('hidden'); qs('#pf_msg').textContent = '로그인이 필요합니다.'; return; }
  block.classList.remove('hidden');
  qs('#pf_email').value = user.email || '';
  qs('#pf_nick').value = user.nickname || '';
  qs('#pf_tokens').textContent = JSON.stringify({accessToken, refreshToken: !!refreshToken, role: user.role}, null, 2);
}

async function loadWhoAmI(){
  const out = await guardedRun('modules.auth.login', {action:'WHOAMI', mode:'SINGLE', input:{}});
  state.user = (out.ok && out.data && out.data.id) ? out.data : null;
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
