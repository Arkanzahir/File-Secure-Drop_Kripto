/* File Secure Drop: UI tanpa library. Seluruh operasi kriptografi ada di crypto_core.py. */
'use strict';
const $ = id => document.getElementById(id);
const icon = (name, cls = '') => `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const esc = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let people = [ { id: 'alice', name: 'Alice', initials: 'A', color: 'sage', subtitle: 'Kontak tersimpan' }, { id: 'nadia', name: 'Nadia', initials: 'N', color: 'clay', subtitle: 'Kontak tersimpan' }, { id: 'raka', name: 'Raka', initials: 'R', color: 'blue', subtitle: 'Kontak tersimpan' } ];
let allPeople = [{id:'bob',name:'Bob',initials:'B',color:'sage'}, ...people];
let current='bob', token=sessionStorage.getItem('filedrop-token') || '';
const person = id => allPeople.find(p => p.id === id) || people[0];
let recipient = 'alice', view = 'send', files = [], message = '', query = '', sending = false, success = null, nextId = 10, toastTimer;
let records = [];

function bytes(n) { if (n < 1024) return `${n} B`; const unit = n < 1048576 ? 'KB' : 'MB'; const value = n / (unit === 'KB' ? 1024 : 1048576); return `${value.toLocaleString('id-ID', { maximumFractionDigits: 1 })} ${unit}`; }
function extension(name) { const parts = name.split('.'); return parts.length > 1 ? parts.at(-1).toUpperCase().slice(0, 5) : 'FILE'; }
function fileIcon(name, large = false) { const ext = extension(name), kind = ext === 'PDF' ? 'pdf' : ['DOC', 'DOCX', 'TXT'].includes(ext) ? 'document' : ['ZIP', 'RAR', '7Z'].includes(ext) ? 'archive' : 'other'; return `<span class="file-icon ${kind} ${large ? 'large' : ''}" aria-hidden="true">${icon('file')}<span>${esc(ext)}</span></span>`; }
function avatar(id, size = '') { const p = person(id); return `<span class="avatar ${p.color} ${size}">${p.initials}</span>`; }
function toast(text) { $('toast').textContent = text; $('toast').classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('show'), 3500); }
function go(next) { if (sending) return; view = next; success = null; query = ''; $('search').value = ''; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); }
function renderNav() {
  const current = ({ send: 'Kirim file', inbox: 'Kotak masuk', sent: 'Terkirim', contacts: 'Kontak', search: 'Hasil pencarian' })[view];
  $('breadcrumb-current').textContent = current;
  document.querySelectorAll('[data-view]').forEach(b => { b.classList.toggle('active', b.dataset.view === view); if (b.dataset.view === view) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
  document.querySelector('.nav-count').textContent = records.filter(r => r.direction === 'inbox' && r.status === 'Baru').length;
}
function heading(eyebrow, title, subtitle, extra = '') { return `<section class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${subtitle}</p></div>${extra}</section>`; }
function render() {
  renderNav();
  if (view === 'send') { success ? renderSuccess() : renderSend(); }
  else if (view === 'contacts') renderContacts();
  else renderList();
  bindCommon();
}
function renderSend() {
  const p = person(recipient), total = files.reduce((n, f) => n + f.size, 0);
  $('main').innerHTML = heading('BERBAGI DOKUMEN', 'Kirim file<span class="title-dot">.</span>', 'Dokumen penting, untuk orang yang tepat.', `<div class="private-badge">${icon('lock')}Transfer pribadi</div>`) + `<div class="send-layout"><section class="upload-panel"><div class="panel-heading"><h2>File untuk dikirim</h2><span>Maks. 1 MB</span></div><div class="upload-body"><input type="file" multiple id="file-input" hidden><div class="dropzone ${files.length ? 'compact' : ''}" id="dropzone" tabindex="0" role="button" aria-label="Pilih atau tarik file"><div class="upload-art" aria-hidden="true"><span class="art-sheet back"></span><span class="art-sheet front"><span></span><span></span><span></span></span><span class="art-upload">${icon('upload')}</span><span class="art-spark spark-one"></span><span class="art-spark spark-two"></span></div><h3>${files.length ? 'Tambahkan file lain' : 'Tarik filemu ke sini'}</h3><p>atau pilih langsung dari perangkat</p><span class="choose-file">${icon('plus')}Pilih file</span><span class="file-types">Dokumen, gambar, dan arsip</span></div><div id="file-error" role="alert"></div>${files.length ? `<div class="selected-header"><span>${files.length} file dipilih <span class="dot-divider">·</span> ${bytes(total)}</span><button type="button" class="text-button" id="clear-files">Kosongkan</button></div><div class="selected-files">${files.map((f, i) => `<div class="selected-file">${fileIcon(f.name)}<div><strong title="${esc(f.name)}">${esc(f.name)}</strong><span>${bytes(f.size)}</span></div><span class="file-ready">${icon('check')}</span><button class="remove-file icon-button" data-remove="${i}" aria-label="Hapus ${esc(f.name)}">${icon('close')}</button></div>`).join('')}</div>` : `<div class="upload-bottom"><span>${icon('file')}Hingga 5 file per kiriman</span><button id="sample-file" class="text-button">Coba file contoh${icon('arrow')}</button></div>`}</div></section><aside class="recipient-panel"><div class="recipient-content"><div class="eyebrow muted-eyebrow">PENERIMA</div><h2>Untuk siapa?</h2><button class="recipient-select" id="select-recipient" aria-haspopup="dialog">${avatar(recipient)}<span><strong>${p.name}</strong><small>${p.subtitle}</small></span>${icon('chevron')}</button><label for="message" class="message-label">Pesan singkat <span>opsional</span></label><textarea id="message" maxlength="200" placeholder="Ada yang ingin disampaikan?" rows="4">${esc(message)}</textarea><div class="message-count"><span id="message-count">${message.length}</span>/200</div><div class="delivery-note">${icon('shield')}<p>Hanya penerima yang kamu pilih<br>yang mendapatkan kiriman ini.</p></div></div><div class="send-action"><button class="button primary full" id="send-files" ${files.length ? '' : 'disabled'}>${sending ? 'Mengirim…' : 'Kirim file'}${icon('arrow')}</button><span id="send-summary">${files.length ? `${files.length} file · ${bytes(total)} · kepada ${p.name}` : 'Pilih file untuk mulai mengirim'}</span></div></aside></div><section class="recent-section"><div class="section-heading"><div><span class="eyebrow muted-eyebrow">RIWAYAT</span><h2>Kiriman terbaru</h2></div><button class="text-button" data-go="sent">Lihat semua${icon('arrow')}</button></div>${table(records.filter(r => r.direction === 'sent').slice(0, 3), 'PENERIMA')}</section>`;
  const input = $('file-input'), dropzone = $('dropzone');
  dropzone.onclick = () => input.click(); dropzone.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } };
  input.onchange = () => addFiles([...input.files]);
  dropzone.ondragover = e => { e.preventDefault(); dropzone.classList.add('drag-over'); };
  dropzone.ondragleave = () => dropzone.classList.remove('drag-over');
  dropzone.ondrop = e => { e.preventDefault(); dropzone.classList.remove('drag-over'); addFiles([...e.dataTransfer.files]); };
  $('select-recipient').onclick = chooseRecipient;
  $('message').oninput = e => { message = e.target.value; $('message-count').textContent = message.length; };
  if ($('sample-file')) $('sample-file').onclick = () => addFiles([new File(['Contoh file File Secure Drop. File ini benar-benar dienkripsi saat dikirim dan dipulihkan saat diunduh.\n'], 'Catatan praktikum.txt', { type: 'text/plain' })]);
  if ($('clear-files')) $('clear-files').onclick = () => { files = []; render(); };
  document.querySelectorAll('[data-remove]').forEach(b => b.onclick = () => { files.splice(Number(b.dataset.remove), 1); render(); });
  $('send-files').onclick = sendFiles;
}
function addFiles(incoming) {
  const unique = [...files];
  for (const f of incoming) if (!unique.some(old => old.name === f.name && old.size === f.size && old.lastModified === f.lastModified)) unique.push(f);
  if (unique.length > 5 || unique.reduce((n, f) => n + f.size, 0) > 1024 * 1024) { $('file-error').innerHTML = `<div class="inline-error">${icon('help')}Pilih maksimal 5 file dengan total ukuran 1 MB.</div>`; return; }
  files = unique; render();
}
function table(rows, recipientLabel = 'PENERIMA') {
  if (!rows.length) return `<div class="empty-state">${icon('inbox')}<h3>Belum ada file di sini.</h3><p>Kirimanmu akan muncul di halaman ini.</p></div>`;
  return `<div class="file-table-wrap"><table class="file-table"><thead><tr><th>NAMA FILE</th><th>${recipientLabel}</th><th>DIKIRIM</th><th>STATUS</th><th><span class="sr-only">Aksi</span></th></tr></thead><tbody>${rows.map(r => `<tr><td><button class="file-cell" data-detail="${r.id}">${fileIcon(r.name)}<span><strong title="${esc(r.name)}">${esc(r.name)}</strong><small>${bytes(r.size)}</small></span></button></td><td><span class="recipient-cell">${avatar(r.person, 'tiny')}<span>${person(r.person).name}</span></span></td><td><span class="file-date">${formatDate(r.date)}</span></td><td><span class="status ${r.status === 'Terkirim' ? 'pending' : r.status === 'Baru' ? 'new' : 'opened'}">${r.status === 'Sudah dibuka' ? icon('check') : '<span class="status-dot"></span>'}${r.status}</span></td><td><button class="icon-button row-more" data-detail="${r.id}" aria-label="Detail ${esc(r.name)}">${icon('more')}</button></td></tr>`).join('')}</tbody></table></div>`;
}
function renderList() {
  const searchMode = view === 'search', inbox = view === 'inbox';
  const rows = records.filter(r => searchMode ? r.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()) || person(r.person).name.toLocaleLowerCase().includes(query.toLocaleLowerCase()) : r.direction === view);
  $('main').innerHTML = heading(searchMode ? 'PENCARIAN' : inbox ? 'UNTUKMU' : 'DARI RUANGMU', searchMode ? 'Hasil pencarian<span class="title-dot">.</span>' : inbox ? 'Kotak masuk<span class="title-dot">.</span>' : 'File terkirim<span class="title-dot">.</span>', searchMode ? `${rows.length} hasil untuk “${esc(query)}”.` : inbox ? 'Semua file yang dibagikan kepadamu, di satu tempat.' : 'Lihat kembali file yang sudah kamu bagikan.', `<button class="button primary" data-go="send">${icon('plus')}Kirim file baru</button>`) + `<section class="list-panel"><div class="list-toolbar"><span>${rows.length} kiriman</span><span>${icon('clock')}Terbaru lebih dulu</span></div>${table(rows, inbox ? 'PENGIRIM' : 'PENERIMA')}</section>`;
}
function renderContacts() {
  $('main').innerHTML = heading('ORANG-ORANG PILIHANMU', 'Kontak<span class="title-dot">.</span>', 'Kirim file tanpa perlu mencari alamat penerima lagi.') + `<section class="contact-grid">${people.map(p => `<article class="contact-card">${avatar(p.id, 'big')}<h2>${p.name}</h2><p>Kontak tersimpan</p><button class="button secondary" data-contact="${p.id}">Kirim file${icon('arrow')}</button></article>`).join('')}</section>`;
  document.querySelectorAll('[data-contact]').forEach(b => b.onclick = () => { recipient = b.dataset.contact; go('send'); });
}
async function sendFiles() {
  if (!files.length || sending) return;
  const snapshot={files:[...files],person:recipient,note:message};
  sending=true;
  $('send-files').innerHTML='<span class="spinner"></span>Mengirim…';
  document.querySelectorAll('main button,main textarea').forEach(el=>el.disabled=true);
  $('account-switch').disabled=true;
  try {
    const payload=[];
    for(const file of snapshot.files){
      const raw=new Uint8Array(await file.arrayBuffer());
      let binary='';
      for(let i=0;i<raw.length;i+=32768) binary+=String.fromCharCode(...raw.subarray(i,i+32768));
      payload.push({name:file.name,mime:file.type||'application/octet-stream',data:btoa(binary)});
    }
    const data=await api('/api/send',{method:'POST',body:JSON.stringify({recipient:snapshot.person,note:snapshot.note,files:payload})});
    applyState(data);success=snapshot;files=[];message='';sending=false;render();
  }catch(e){sending=false;render();$('file-error').innerHTML='<div class="inline-error" role="alert">'+esc(e.message)+'</div>';}
  finally{$('account-switch').disabled=false;}
}

function renderSuccess() {
  const p = person(success.person), total = success.files.reduce((n, f) => n + f.size, 0);
  $('main').innerHTML = `<section class="success-card"><span class="success-art">${icon('check')}<span></span></span><div class="eyebrow">SAMPAI KE TUJUAN</div><h1>File terkirim<span class="title-dot">.</span></h1><p>${success.files.length} file telah dibagikan kepada <strong>${p.name}</strong>.</p><div class="success-recipient">${avatar(p.id)}<span>${p.name}<small>${success.files.length} file <span class="dot-divider">·</span> ${bytes(total)}</small></span></div><div class="success-file-list">${success.files.map(f => `<div>${fileIcon(f.name)}<span>${esc(f.name)}</span>${icon('check')}</div>`).join('')}</div><div class="success-actions"><button class="button secondary" data-go="sent">Lihat kiriman</button><button class="button primary" data-go="send">Kirim file lagi${icon('arrow')}</button></div><span class="success-caption">Kiriman tersimpan dan tersedia pada akun penerima.</span></section>`;
}
function chooseRecipient() {
  $('contact-options').innerHTML = people.map(p => `<button class="contact-option ${recipient === p.id ? 'chosen' : ''}" data-pick="${p.id}">${avatar(p.id)}<span><strong>${p.name}</strong><small>${p.subtitle}</small></span><span class="radio-mark">${recipient === p.id ? icon('check') : ''}</span></button>`).join('');
  document.querySelectorAll('[data-pick]').forEach(b => b.onclick = () => { recipient = b.dataset.pick; $('contact-dialog').close(); render(); });
  $('contact-dialog').showModal();
}
async function openDetail(id) {
  const r=records.find(r=>r.id===id);if(!r)return;
  $('detail-title').textContent=r.name;
  $('detail-content').innerHTML=`<div class="detail-file-preview">${fileIcon(r.name,true)}<span>${bytes(r.size)} · ${esc(extension(r.name))}</span></div><div class="detail-fields"><div><span>${r.direction==='inbox'?'Dari':'Kepada'}</span><strong>${avatar(r.person,'tiny')}${person(r.person).name}</strong></div><div><span>Dikirim</span><strong>${formatDate(r.date)}</strong></div></div><div id="detail-note-content"><p class="detail-caption">Membuka informasi file…</p></div><button class="button primary full" id="download-file" disabled>${icon('down')}Unduh file</button><p class="detail-caption">File dipulihkan otomatis saat dibuka.</p>`;
  $('detail-dialog').showModal();
  try{
    const info=await api('/api/files/'+id);
    if(!$('detail-dialog').open)return;
    $('detail-note-content').innerHTML=info.note?`<div class="detail-message"><span>PESAN SINGKAT</span><p>${esc(info.note)}</p></div>`:'';
    $('download-file').disabled=false;
    $('download-file').onclick=async()=>{
      const b=$('download-file');b.disabled=true;b.innerHTML='<span class="spinner"></span>Menyiapkan file…';
      try{
        const response=await fetch('/api/files/'+id+'/download',{headers:{Authorization:'Bearer '+token}});
        if(!response.ok){const e=await response.json();throw Error(e.error||'File gagal dibuka.');}
        const blob=await response.blob();const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=r.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        toast('File berhasil dipulihkan dan diunduh.');
      }catch(e){toast(e.message);}finally{b.disabled=false;b.innerHTML=icon('down')+'Unduh file';}
    };
    await refreshState(false);
  }catch(e){$('detail-note-content').innerHTML='<div class="inline-error" role="alert">'+esc(e.message)+'</div>';}
}

function bindCommon() {
  document.querySelectorAll('[data-go]').forEach(b => b.onclick = () => go(b.dataset.go));
  document.querySelectorAll('[data-detail]').forEach(b => b.onclick = () => openDetail(b.dataset.detail));
}
$('side-contacts').innerHTML = people.map(p => `<button class="side-contact" data-side-contact="${p.id}">${avatar(p.id, 'small')}<span>${p.name}</span><svg><use href="#i-arrow"/></svg></button>`).join('');
document.querySelectorAll('[data-side-contact]').forEach(b => b.onclick = () => { recipient = b.dataset.sideContact; go('send'); });
document.querySelectorAll('[data-view]').forEach(b => b.onclick = () => go(b.dataset.view));
document.querySelector('.brand').onclick = e => { e.preventDefault(); go('send'); };
$('search').oninput = e => { if (sending) return; query = e.target.value.trim(); view = query ? 'search' : 'send'; success = null; render(); };
document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); $('search').focus(); } });
document.querySelectorAll('.close-dialog').forEach(b => b.onclick = () => { const d = b.closest('dialog'); d.close(); if (d.id === 'detail-dialog') render(); });
document.querySelectorAll('dialog').forEach(d => d.addEventListener('click', e => { const r = d.getBoundingClientRect(); if (e.target === d && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) d.close(); }));
$('help-button').onclick = () => $('help-dialog').showModal();
$('profile-button').onclick = chooseAccount;
$('account-switch').onclick = chooseAccount;
boot();


function formatDate(date){return new Date(date).toLocaleString('id-ID',{timeZone:'Asia/Jakarta',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});}
async function api(path,options={}){
  const response=await fetch(path,{...options,headers:{'Content-Type':'application/json',Authorization:'Bearer '+token,...options.headers}});
  const data=await response.json();if(!response.ok)throw Error(data.error||'Permintaan gagal.');return data;
}
function applyState(data){
  current=data.current;allPeople=data.users.map(p=>({...p,subtitle:'Kontak tersimpan'}));people=allPeople.filter(p=>p.id!==current).map(p=>({...p,subtitle:'Kontak tersimpan'}));records=data.records;
  if(!people.some(p=>p.id===recipient))recipient=people[0].id;
  const me=person(current);
  document.querySelector('.profile-avatar').textContent=me.initials;
  document.querySelector('.profile-button strong').textContent=me.name;
  document.querySelector('.profile-button small').textContent='Ganti akun';
  $('account-switch').textContent='Akun: '+me.name;
  $('side-contacts').innerHTML=people.map(p=>`<button class="side-contact" data-side-contact="${p.id}">${avatar(p.id,'small')}<span>${p.name}</span>${icon('arrow')}</button>`).join('');
  document.querySelectorAll('[data-side-contact]').forEach(b=>b.onclick=()=>{recipient=b.dataset.sideContact;go('send');});
}
async function login(user){
  const data=await api('/api/login',{method:'POST',body:JSON.stringify({user})});token=data.token;sessionStorage.setItem('filedrop-token',token);applyState(data);files=[];message='';view='send';success=null;render();
}
function chooseAccount(){
  if(sending)return;
  $('account-options').innerHTML=allPeople.map(p=>`<button class="contact-option ${p.id===current?'chosen':''}" data-account="${p.id}">${avatar(p.id)}<span><strong>${p.name}</strong><small>${p.id===current?'Sedang digunakan':'Buka ruang file'}</small></span><span class="radio-mark">${p.id===current?icon('check'):''}</span></button>`).join('');
  document.querySelectorAll('[data-account]').forEach(b=>b.onclick=async()=>{try{await login(b.dataset.account);$('account-dialog').close();toast('Masuk sebagai '+person(current).name);}catch(e){toast(e.message);}});
  $('account-dialog').showModal();
}
async function refreshState(redraw=true){const data=await api('/api/state');const changed=JSON.stringify(data.records)!==JSON.stringify(records);applyState(data);renderNav();if(redraw&&changed&&view!=='send'&&!document.querySelector('dialog[open]'))render();}
async function boot(){
  $('main').innerHTML='<div class="empty-state"><h3>Memuat ruang file…</h3></div>';
  try{if(token){try{applyState(await api('/api/state'));render();}catch{await login('bob');}}else await login('bob');}
  catch(e){$('main').innerHTML='<div class="empty-state"><h3>Server belum tersambung.</h3><p>Jalankan JALANKAN.bat, kemudian buka halaman ini kembali.</p></div>';}
}
setInterval(()=>{if(token&&!sending)refreshState().catch(()=>{});},6000);


