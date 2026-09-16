'use strict';
const csrf=document.querySelector('meta[name="csrf-token"]').content;
const $=s=>document.querySelector(s);
const $$=s=>Array.from(document.querySelectorAll(s));
$$('form[data-confirm]').forEach(form=>form.addEventListener('submit',e=>{if(!confirm(form.dataset.confirm))e.preventDefault();}));
let previews=[];
function previewPhotos(){
 const container=$('#photo-preview');if(!container)return;
 previews.forEach(URL.revokeObjectURL);previews=[];container.replaceChildren();
 const files=[...($('#gallery')?.files||[]),...($('#camera')?.files||[])];
 files.forEach(file=>{if(!file.type.startsWith('image/'))return;const url=URL.createObjectURL(file);previews.push(url);const img=document.createElement('img');img.src=url;img.alt='선택한 사진 미리보기';container.append(img);});
}
$('#gallery')?.addEventListener('change',previewPhotos);$('#camera')?.addEventListener('change',previewPhotos);
let dirty=false;
$('#entry-form')?.addEventListener('input',()=>dirty=true);$('#entry-form')?.addEventListener('submit',()=>dirty=false);
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
async function jsonRequest(url,options={}){
 const response=await fetch(url,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,...options.headers}});
 let body;try{body=await response.json();}catch{throw new Error('서버 응답을 확인할 수 없어요. 로그인 상태를 확인해주세요.');}
 if(!response.ok)throw new Error(body.error?.message||'요청을 처리하지 못했어요.');return body.data;
}
const publishButton=$('#publish');let watching=false;
function storageKey(){return 'daynews-job:'+publishButton?.dataset.date;}
async function watchJob(id){
 if(watching)return;watching=true;const dialog=$('#publishing');if(!dialog.open)dialog.showModal();publishButton.disabled=true;
 try{
  for(let retry=0;retry<600;retry++){
   const job=await jsonRequest('/api/v1/publications/'+encodeURIComponent(id));$('#progress').value=job.progress;
   $('#progress-text').textContent=job.progress<85?'기자들이 기록을 읽고 있어요.':'신문의 마지막 페이지를 다듬고 있어요.';
   if(job.status==='succeeded'){sessionStorage.removeItem(storageKey());location.assign(job.url);return;}
   if(job.status==='failed')throw new Error(job.error||'발행에 실패했어요. 다시 시도해주세요.');
   await new Promise(resolve=>setTimeout(resolve,1500));
  }
  throw new Error('작업 시간이 길어지고 있어요. 잠시 후 대기실을 다시 열어주세요.');
 }catch(error){dialog.close();$('#publish-error').textContent=error.message;sessionStorage.removeItem(storageKey());publishButton.dataset.key=crypto.randomUUID();}
 finally{publishButton.disabled=false;watching=false;}
}
publishButton?.addEventListener('click',async()=>{
 const included=$$('input[name="include"]:checked').map(x=>x.value);const highlight=$('input[name="highlight"]:checked')?.value;
 const error=$('#publish-error');error.textContent='';
 if(!included.length){error.textContent='신문에 넣을 기록을 골라주세요.';return;}
 if(!highlight||!included.includes(highlight)){error.textContent='포함된 기록 중 하나를 1면 하이라이트로 골라주세요.';return;}
 publishButton.disabled=true;
 try{
  const result=await jsonRequest('/api/v1/publications',{method:'POST',headers:{'Idempotency-Key':publishButton.dataset.key},body:JSON.stringify({date:publishButton.dataset.date,entry_ids:included,highlight_id:highlight,automatic:$$('#auto-form input[name="automatic"]:checked').map(x=>x.value)})});
  sessionStorage.setItem(storageKey(),result.id);await watchJob(result.id);
 }catch(e){error.textContent=e.message;}finally{publishButton.disabled=false;}
});
if(publishButton){const pending=publishButton.dataset.pending||sessionStorage.getItem(storageKey());if(pending)watchJob(pending);}
$('#publishing')?.addEventListener('cancel',e=>{e.preventDefault();});
let shareFile=null;const nativeShare=$('#native-share');
nativeShare?.addEventListener('click',async()=>{
 const feedback=$('#share-feedback');
 if(!shareFile){nativeShare.disabled=true;feedback.textContent='공유용 이미지를 준비하고 있어요.';
  try{const response=await fetch(nativeShare.dataset.image);if(!response.ok)throw new Error();shareFile=new File([await response.blob()],'my-daynews.png',{type:'image/png'});nativeShare.textContent='준비 완료 · 공유창 열기';feedback.textContent='한 번 더 눌러 공유할 앱을 선택해주세요.';}
  catch{feedback.textContent='이미지를 준비하지 못했어요. 이미지 저장 버튼을 이용해주세요.';}
  finally{nativeShare.disabled=false;}return;
 }
 if(navigator.canShare?.({files:[shareFile]})&&navigator.share){
  try{await navigator.share({files:[shareFile],title:'나의 하루신문'});feedback.textContent='공유창에 이미지를 전달했어요.';}
  catch(e){feedback.textContent=e.name==='AbortError'?'공유를 취소했어요. 신문은 보관되어 있어요.':'공유를 지원하지 않는 환경이에요. 이미지 저장을 이용해주세요.';}
 }else{const a=document.createElement('a');const url=URL.createObjectURL(shareFile);a.href=url;a.download=shareFile.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);feedback.textContent='이미지를 저장했어요. Instagram에서 사진을 선택해 올려주세요.';}
});
$('#copy-link')?.addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#share-link').value);$('#copy-status').textContent='링크를 복사했어요.';}catch{$('#share-link').select();$('#copy-status').textContent='선택된 링크를 직접 복사해주세요.';}});
