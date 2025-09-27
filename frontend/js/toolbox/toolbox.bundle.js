var Toolbox=(()=>{var W=Object.defineProperty;var xt=Object.getOwnPropertyDescriptor;var wt=Object.getOwnPropertyNames;var yt=Object.prototype.hasOwnProperty;var E=(p,t)=>{for(var e in t)W(p,e,{get:t[e],enumerable:!0})},vt=(p,t,e,s)=>{if(t&&typeof t=="object"||typeof t=="function")for(let o of wt(t))!yt.call(p,o)&&o!==e&&W(p,o,{get:()=>t[o],enumerable:!(s=xt(t,o))||s.enumerable});return p};var kt=p=>vt(W({},"__esModule",{value:!0}),p);var At={};E(At,{ActionItem:()=>q,CheckboxItem:()=>j,ContextMenu:()=>N,DataTable:()=>S,EditableText:()=>M,LoadingScreen:()=>U,MenuItem:()=>C,Navigator:()=>z,PopUp:()=>T,SeparatorItem:()=>A,Toast:()=>F,context_menu:()=>J,editable_text:()=>K,loading_screen:()=>ot,navigator:()=>V,pop_up:()=>X,table:()=>st,toast:()=>it});var J={};E(J,{ActionItem:()=>q,CheckboxItem:()=>j,ContextMenu:()=>N,MenuItem:()=>C,SeparatorItem:()=>A});var nt=`.context-menu{position:fixed;z-index:9999;min-width:180px;max-width:320px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,.12);padding:6px 0;font:14px/1.4 system-ui,-apple-system,Segoe UI,Roboto}\r
.context-menu__item{display:flex;gap:8px;align-items:center;padding:8px 12px;cursor:pointer;user-select:none;white-space:nowrap}\r
.context-menu__item:hover{background:#f5f5f7}\r
.context-menu__item[aria-disabled="true"]{opacity:.5;pointer-events:none;cursor:default}\r
.context-menu__icon{width:16px;height:16px;display:inline-flex;align-items:center;justify-content:center;flex:0 0 16px}\r
.context-menu__label{flex:1 1 auto;overflow:hidden;text-overflow:ellipsis}\r
.context-menu__check{margin-left:auto}\r
.context-menu__sep{height:1px;background:#eee;margin:6px 0}\r
.context-menu__item--danger:hover{background:#fee2e2}`;function y(p,t){if(typeof document>"u"||t&&document.getElementById(t))return;let e=document.createElement("style");t&&(e.id=t),e.textContent=p,document.head.appendChild(e)}var C=class{visible(t){return!0}enabled(t){return!0}render(t,e){throw new Error("implement render()")}},q=class extends C{constructor({label:t,on_click:e,icon_html:s=null,visible:o=null,enabled:i=null,danger:n=!1}){super(),this.label=t,this.on_click=e,this.icon_html=s,this.danger=!!n,o&&(this.visible=o),i&&(this.enabled=i)}render(t,e){let s=document.createElement("div");return s.className="context-menu__item"+(this.danger?" context-menu__item--danger":""),s.setAttribute("role","menuitem"),s.innerHTML=`${this.icon_html?`<span class="context-menu__icon">${this.icon_html}</span>`:""}<span class="context-menu__label">${this.label}</span>`,this.enabled(t)?s.addEventListener("click",o=>{o.stopPropagation(),e.close(),this.on_click?.(t)}):s.setAttribute("aria-disabled","true"),s}},j=class extends C{constructor({label:t,get_checked:e,on_toggle:s,visible:o=null,enabled:i=null}){super(),this.label=t,this.get_checked=e,this.on_toggle=s,o&&(this.visible=o),i&&(this.enabled=i)}render(t,e){let s=!!this.get_checked?.(t),o=document.createElement("div");return o.className="context-menu__item",o.setAttribute("role","menuitemcheckbox"),o.setAttribute("aria-checked",String(s)),o.innerHTML=`<span class="context-menu__label">${this.label}</span><span class="context-menu__check">${s?"\u2713":""}</span>`,this.enabled(t)?o.addEventListener("click",i=>{i.stopPropagation(),this.on_toggle?.(!s,t),e.close()}):o.setAttribute("aria-disabled","true"),o}},A=class extends C{render(){let t=document.createElement("div");return t.className="context-menu__sep",t.setAttribute("role","separator"),t}},N=class{constructor({activation:t="contextmenu",mode:e="always",selector:s=null,container:o=document,items:i=[],context_fn:n=null}={}){this.activation=t,this.mode=e,this.selector=s,this.container=o,this.items=i,this.context_fn=n,this.menu_el=this._create_root(),this.is_open=!1,this._bind()}set_items(t){this.items=t??[]}add_item(t){this.items.push(t)}items_list(t=[]){for(let e of t)this.add_item(e);return this}action(t,e,s={}){return this.add_item(new q({label:t,on_click:e,...s||{}})),this}check(t,e,s,o={}){return this.add_item(new j({label:t,get_checked:e,on_toggle:s,...o||{}})),this}sep(){return this.add_item(new A),this}open_for_event(t){let e=this._resolve_target(t);if(!e)return;t.preventDefault?.(),t.stopPropagation?.();let s=this._build_ctx(t,e);this._render_items(s),this._open_at(t.clientX??0,t.clientY??0)}open_at(t,e,s={}){this._render_items(s),this._open_at(t,e)}close(){this.is_open&&(this.is_open=!1,this.menu_el.style.display="none",document.removeEventListener("click",this._on_doc_click,!0),document.removeEventListener("keydown",this._on_doc_key,!0),window.removeEventListener("resize",this._on_win_resize,!0),window.removeEventListener("scroll",this._on_win_resize,!0))}destroy(){this.close(),this.menu_el.remove(),this._unbind()}_create_root(){let t=document.createElement("div");return t.className="context-menu",t.style.display="none",t.setAttribute("role","menu"),document.body.appendChild(t),t}_bind(){let t=Array.isArray(this.activation)?this.activation:[this.activation];this._on_trigger=e=>this.open_for_event(e);for(let e of t)this.container.addEventListener(e,this._on_trigger)}_unbind(){let t=Array.isArray(this.activation)?this.activation:[this.activation];if(this._on_trigger)for(let e of t)this.container.removeEventListener(e,this._on_trigger)}_resolve_target(t){return this.mode==="always"?t.target:this.mode==="selector"&&this.selector?t.target.closest(this.selector):null}_build_ctx(t,e){return{event:t,target:e,data:e?.dataset??{},...this.context_fn?this.context_fn(t,e)||{}:{}}}_render_items(t){this.menu_el.innerHTML="";for(let e of this.items){if(!e.visible(t))continue;let s=e.render(t,this);this.menu_el.appendChild(s)}if(!this.menu_el.childElementCount){let e=document.createElement("div");e.className="context-menu__item",e.textContent="No actions",e.setAttribute("aria-disabled","true"),this.menu_el.appendChild(e)}}_open_at(t,e){this.menu_el.style.display="block",this.menu_el.style.left="0px",this.menu_el.style.top="0px";let{width:s,height:o}=this.menu_el.getBoundingClientRect(),i=document.documentElement.clientWidth,n=document.documentElement.clientHeight,a=Math.min(t,i-s-4),r=Math.min(e,n-o-4);this.menu_el.style.left=`${Math.max(4,a)}px`,this.menu_el.style.top=`${Math.max(4,r)}px`,this.is_open=!0,this._on_doc_click=l=>{this.menu_el.contains(l.target)||this.close()},this._on_doc_key=l=>{l.key==="Escape"&&this.close()},this._on_win_resize=()=>this.close(),document.addEventListener("click",this._on_doc_click,!0),document.addEventListener("keydown",this._on_doc_key,!0),window.addEventListener("resize",this._on_win_resize,!0),window.addEventListener("scroll",this._on_win_resize,!0)}};y(nt,"webtool__context_menu_css");var K={};E(K,{EditableText:()=>M});var rt=`.editable-text{display:inline-block;position:relative}\r
.editable-text .edit{display:none;font:inherit;border:1px solid #ccc;padding:2px 6px;background:transparent}\r
.editable-text.is-editing .view{display:none}\r
.editable-text.is-editing .edit{display:inline-block}\r
`;var M=class p{static _reg=new Map;static _inited=!1;static _esc(t){return String(t).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;")}static _uid(){return"et_"+Math.random().toString(36).slice(2,8)+Date.now().toString(36)}constructor({value:t,tag:e="h2",id:s=null,on_save:o=null,on_cancel:i=null}){this.id=s||p._uid(),this.value=t??"",this.tag=e,this.on_save=o,this.on_cancel=i,p._reg.set(this.id,this),p.init()}toString(){let t=p._esc(this.value);return`<div class="editable-text" data-editable-id="${this.id}">
        <${this.tag} class="view">${t}</${this.tag}>
        <input class="edit" type="text" value="${t}">
      </div>`}static init(){p._inited||(p._inited=!0,document.addEventListener("dblclick",t=>{let e=t.target.closest(".editable-text");if(!e)return;let s=e.querySelector(".edit"),i=e.querySelector(".view").textContent.trim();e.setAttribute("data-initial",i),s.value=i,e.classList.add("is-editing"),s.size=Math.max(1,s.value.length),s.focus(),s.select()}),document.addEventListener("keydown",t=>{if(!t.target.matches(".editable-text.is-editing .edit"))return;let e=t.target.closest(".editable-text");if(t.key==="Enter")t.preventDefault(),p._commit(e);else if(t.key==="Escape")t.preventDefault(),p._cancel(e);else if(t.key.length===1){let s=e.querySelector(".edit");queueMicrotask(()=>s.size=Math.max(1,s.value.length))}}),document.addEventListener("blur",t=>{t.target.matches(".editable-text.is-editing .edit")&&p._commit(t.target.closest(".editable-text"))},!0))}static async _commit(t){if(!t||!t.classList.contains("is-editing"))return;let e=t.querySelector(".edit"),s=t.querySelector(".view"),o=p._reg.get(t.getAttribute("data-editable-id")),i=t.getAttribute("data-initial")??s.textContent.trim(),n=(e.value||"").trim();if(t.classList.remove("is-editing"),!n||n===i){e.value=i;return}let a=s.textContent;s.textContent=n;try{if(o?.on_save){let r=o.on_save(n,o);r&&typeof r.then=="function"&&await r}o&&(o.value=n)}catch(r){s.textContent=a,e.value=a,console.error("editable_text save failed:",r)}}static _cancel(t){if(!t)return;let e=t.querySelector(".edit"),s=t.querySelector(".view"),o=p._reg.get(t.getAttribute("data-editable-id"));e.value=t.getAttribute("data-initial")??s.textContent.trim(),t.classList.remove("is-editing");try{o?.on_cancel?.(o)}catch{}}};y(rt,"webtool__editable_text_css");var V={};E(V,{Navigator:()=>z});var at=`\r
.navigator {\r
    width: 100%;\r
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;\r
    border-radius: 8px;\r
    overflow: hidden;\r
}\r
\r
.navigator-bar {\r
    display: flex;\r
    gap: 0.25rem;\r
    border-bottom: 1px solid rgba(0,0,0,0.05);\r
    position: relative;\r
    z-index: 2;\r
}\r
\r
.navigator-tab {\r
    background: #f1f3f5;\r
    color: #495057;\r
    border: 1px solid transparent;\r
    border-radius: 6px 6px 0 0;\r
    padding: 0.3rem 1rem;\r
    cursor: pointer;\r
    transition: all 0.2s ease-in-out;\r
    position: relative;\r
    top: 2px;\r
    z-index: 1;\r
    margin-bottom: 2px;\r
    display: flex;\r
    align-items: center;\r
    gap: 4px;\r
}\r
\r
.navigator-tab > span {\r
    font-size: 18px;\r
}\r
\r
.navigator-tab:hover {\r
    background-color: #dee2e6;\r
}\r
\r
.navigator-tab.active {\r
    background: #fff;\r
    color: #0d6efd;\r
    border: 1px solid rgba(0,0,0,0.1);\r
    border-bottom: 1px solid #fff; /* Seamless with content */\r
    z-index: 3;\r
    font-weight: 500;\r
    margin: 0;\r
}\r
\r
.navigator-content {\r
    background: #fff;\r
    padding: 18px;\r
    border-radius: 0 0 8px 8px;\r
    border: 1px solid rgba(0,0,0,0.1);\r
    position: relative;\r
    top: -1px;\r
    z-index: 1;\r
}\r
\r
.print-bundle { display: none; }\r
\r
@media print {\r
  /* n\u2019imprimer que le bundle */\r
  body:has( .print-bundle) > *:not(.print-bundle) { display: none !important; }\r
  .print-bundle { display: flex !important; flex-direction: column; break-inside: auto;}\r
\r
  /* couleurs/fonds conserv\xE9s */\r
  html, body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }\r
\r
\r
  .print-page {\r
    display: block;\r
    width: auto !important;\r
    overflow: visible !important;\r
    border: none !important;\r
    break-inside: avoid;\r
    break-before: page;\r
    break-after: page;\r
  }\r
\r
  /* Neutraliser des styles web potentiellement g\xEAnants */\r
  .print-bundle .navigator-content,\r
  .print-bundle .data-wrapper {\r
    width: auto !important;\r
    max-height: none !important;\r
    overflow: visible !important;\r
    box-shadow: none !important;\r
    padding: 0 !important;\r
    margin: 0 !important;\r
    break-inside: auto;\r
  }\r
}\r
`;var z=class p{constructor(t=-1,e=null,s=null,o=null){this.tabs=new Map,this.current=null,this.max_tab_number=t,this.max_tab_message=e,this.tab_count=0,this.delete_event=o,this.open_tab_event=s}draw(t){let e=typeof t=="string"?document.querySelector(t):t;this.container=document.createElement("div"),this.container.className="navigator",this.navbar=document.createElement("div"),this.navbar.className="navigator-bar",this.content_area=document.createElement("div"),this.content_area.className="navigator-content",this.container.appendChild(this.navbar),this.container.appendChild(this.content_area),e.appendChild(this.container)}add(t,e,s,{closable:o=!1,hidden:i=!1,count_towards_limit:n=!0}={}){if(this.tabs.has(t))return;if(n&&this.max_tab_number>=0&&this.tab_count===this.max_tab_number){this.max_tab_message&&toast("warning",this.max_tab_message);return}n&&(this.tab_count+=1);let a=null;if(!i){if(a=document.createElement("button"),a.className="navigator-tab",a.id=t,a.textContent=e,a.addEventListener("click",()=>this.open(t)),o){let l=document.createElement("span");l.className="material-symbols-outlined btn-close",l.innerHTML="close",l.addEventListener("click",c=>{c.stopPropagation(),this.delete(t)}),a.appendChild(l)}this.navbar.appendChild(a)}let r=document.createElement("div");r.id=t,r.style.display="none",typeof s=="string"?r.innerHTML=s:r.appendChild(s.cloneNode(!0)),this.content_area.appendChild(r),this.tabs.set(t,{label:e,button:a,content:r,hidden:!!i,count_towards_limit:!!n}),!this.current&&!i&&this.open(t)}add_hidden(t,e,s,o={}){return this.add(t,e,s,{...o,hidden:!0})}set(t,e){let s=this.tabs.get(t);s&&(s.content.innerHTML="",typeof e=="string"?s.content.innerHTML=e:s.content.appendChild(e.cloneNode(!0)))}open(t){if(!this.tabs.has(t)){console.error(`tab id: <${t}> not found in <${Array.from(this.tabs.keys())}>`);return}if(this.open_tab_event?.(t),this.current&&this.tabs.has(this.current)){let s=this.tabs.get(this.current);s.button?.classList.remove("active"),s.content.style.display="none"}let e=this.tabs.get(t);e.button?.classList.add("active"),e.content.style.display="block",this.current=t}delete(t){let e=this.tabs.get(t);if(e&&(this.delete_event?.(t),e.button?.remove(),e.content.remove(),this.tabs.delete(t),e.count_towards_limit&&(this.tab_count-=1),this.current===t)){let s=this.tabs.keys().next().value;this.current=null,s&&this.open(s)}}order(t){let e=[];for(let s of t){let o=this.tabs.get(s);o?.button&&e.push(o.button)}e.length&&this.navbar.append(...e)}ids({include_hidden:t=!1}={}){let e=[];for(let[s,o]of this.tabs.entries())(t||!o.hidden)&&e.push(s);return e}static from(t,{max_tab_number:e=-1,max_tab_message:s=null,delete_event:o=null}={}){let i=new p(e,s,null,o);return i.container=t,i.container.classList.contains("navigator")||i.container.classList.add("navigator"),i.navbar=i.container.querySelector(".navigator-bar"),i.content_area=i.container.querySelector(".navigator-content"),i.container.querySelectorAll("[data-tab-id]").forEach(n=>{let a=n.getAttribute("data-tab-id"),r=n.getAttribute("data-tab-name")||a,l=n.getAttribute("data-closable")==="true",c=n.getAttribute("data-hidden")==="true",_=n.querySelector(".navigator-tab-content");i.add(a,r,_,{closable:l,hidden:c})}),i}print_tabs(t,{filename:e=null}={}){let s=document.title;e&&(document.title=e);let o=document.createElement("div");o.className="print-bundle";for(let n of t){let a=this.tabs.get(n);if(!a)continue;let r=document.createElement("section");r.className="print-page navigator-content";let l=a.content.cloneNode(!0);l.style.removeProperty("display"),l.querySelectorAll('[style*="display: none"]').forEach(c=>c.style.removeProperty("display")),l.querySelectorAll("canvas").forEach(c=>{try{let _=new Image;_.src=c.toDataURL("image/png"),_.width=c.width,_.height=c.height,c.replaceWith(_)}catch{}}),r.appendChild(l),o.appendChild(r)}document.body.appendChild(o);let i=()=>{o.remove(),document.title=s,window.removeEventListener("afterprint",i)};window.addEventListener("afterprint",i),setTimeout(()=>window.print(),0)}};y(at,"webtool__navigator_css");var X={};E(X,{PopUp:()=>T});var lt=`/* PopUp \u2013 styles unifi\xE9s, sans blur */\r
.pop-up-wrapper{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:9999}\r
.pop-up-backdrop{position:absolute;inset:0;background:rgba(0,0,0,.45)}\r
.showcase-background{position:absolute;inset:0;pointer-events:none;outline:9999px solid rgba(0,0,0,.35)}\r
\r
.pop-up{\r
  position:relative;min-width:280px;max-width:90vw;max-height:90vh;overflow:auto;\r
  background:#fff;border:1px solid #e5e7eb;border-radius:10px;\r
  box-shadow:0 12px 32px rgba(0,0,0,.18);padding:16px\r
}\r
\r
.pop-up .title{font-size:1.5rem;margin-bottom:14px;width:100%;text-align:center}\r
.pop-up-message{margin-bottom:12px}\r
\r
.pop-up-buttons{display:flex; gap:8px; justify-content:flex-end; margin-top:16px}\r
\r
/* Boutons \u2014 pas de transform, effet net via background/border/shadow + anneau ::after */\r
.pop-up button{\r
  position: relative; padding:6px 20px; cursor:pointer;\r
  border: 1px solid #e5e7eb; background:#f8fafc;\r
  transition: background-color .18s ease, border-color .18s ease, box-shadow .18s ease;\r
}\r
.pop-up button:hover{\r
  box-shadow:0 2px 8px rgba(0,0,0,.06), 0 6px 18px rgba(0,0,0,.08);\r
}\r
.pop-up button::after{\r
  content:""; position:absolute; inset:-1px; border-radius:inherit;\r
  box-shadow:0 0 0 0 rgba(59,130,246,.28); opacity: 0; pointer-events:none;\r
  transition:box-shadow .18s ease, opacity .18s ease;\r
}\r
.pop-up button:hover::after{ box-shadow:0 0 0 2px rgba(59,130,246,.16); opacity:1 }\r
\r
.pop-up button:focus-visible{ outline: 1px solid #94a3b8; outline-offset: 1px }\r
\r
\r
button.yes-button {\r
    background-color: #e0f7e9;\r
    border: solid 1px #34c759;\r
    color: #34c759;\r
    border-radius: 4px;\r
}\r
\r
button.no-button {\r
    background-color: #fbe2e0;\r
    border: solid 1px #d4342b;\r
    color: #d4342b;\r
    border-radius: 4px;\r
}\r
\r
button.next-button {\r
    background-color: #d8f2fd;\r
    border: solid 1px #7a9bb0;\r
    color: #7a9bb0;\r
    border-radius: 4px;\r
}\r
\r
`;var T=class p{static _id=0;constructor({content:t="",backdrop:e=!0,backdrop_click_closes:s=!0,esc_closes:o=!0,extra_backdrop_class:i=null,buttons:n=[],on_open:a=null,on_close:r=null}={}){if(this.id=`pop-up-${p._id++}`,this.on_open=a,this.on_close=r,this._wrapper=document.createElement("div"),this._wrapper.className="pop-up-wrapper",this._wrapper.id=this.id,e&&(this._backdrop=document.createElement("div"),this._backdrop.className="pop-up-backdrop",this._wrapper.appendChild(this._backdrop),s&&this._backdrop.addEventListener("click",()=>this.close())),i){let l=document.createElement("div");l.className=i,this._wrapper.appendChild(l)}this._dialog=document.createElement("div"),this._dialog.className="pop-up",this._wrapper.appendChild(this._dialog),this._message=document.createElement("div"),this._message.className="pop-up-message",this._dialog.appendChild(this._message),this._buttons=document.createElement("div"),this._buttons.className="pop-up-buttons",this._dialog.appendChild(this._buttons),this.set_content(t),this.replace_buttons(n),this._on_keydown=l=>{l.key==="Escape"&&o&&this.close()}}set_content(t){return t instanceof Node?this._message.replaceChildren(t):this._message.innerHTML=t??"",this}add_button({label:t,class_name:e="",auto_close:s=!0,on_click:o=null}){let i=document.createElement("button");return e&&(i.className=e),i.textContent=t,i.addEventListener("click",()=>{o&&o(),s&&this.close()}),this._buttons.appendChild(i),this}replace_buttons(t=[]){this._buttons.replaceChildren();for(let e of t)this.add_button(e);return this}open(){return document.body.appendChild(this._wrapper),document.addEventListener("keydown",this._on_keydown,!0),this.on_open&&this.on_open(this),this}close(){return this._wrapper.isConnected?(document.removeEventListener("keydown",this._on_keydown,!0),this._wrapper.remove(),this.on_close&&this.on_close(this),this):this}static confirm(t,{yes_label:e="Yes",no_label:s="No",on_yes:o=null,on_no:i=null}={}){return new p({content:t,buttons:[{label:e,class_name:"yes-button",auto_close:!0,on_click:o},{label:s,class_name:"no-button",auto_close:!0,on_click:i}]})}static next(t,{text:e="Next",on_next:s=null,backdrop:o=!0,backdrop_click_closes:i=!1,before_open:n=null}={}){return new p({content:t,backdrop:o,backdrop_click_closes:i,buttons:[{label:e,class_name:"next-button",auto_close:!0,on_click:s}],on_open:a=>{n&&n(a._dialog)}})}static showcase(t){return new p({content:t,backdrop:!0,extra_backdrop_class:"showcase-background"})}};y(lt,"webtool__pop_up_css");var st={};E(st,{DataTable:()=>S});var dt=`/* .dtbl{border-collapse:collapse;width:100%}\r
.dtbl-sticky thead th{position:sticky;top:0;background:#fff;z-index:1}\r
.dtbl thead th{border-bottom:1px solid #e5e7eb;padding:.45rem .55rem;white-space:nowrap}\r
.dtbl td{padding:.4rem .55rem;border-bottom:1px solid #f1f5f9}\r
.dtbl tbody tr:nth-child(odd){background:#fafafa}\r
.dtbl thead th .dtbl-sort{margin-left:.35rem;opacity:.6;font-size:.8em}\r
.dtbl-toolbar{display:flex;gap:.5rem;align-items:center;margin:.5rem 0;flex-wrap:wrap}\r
.dtbl-search{padding:.35rem .5rem;min-width:240px}\r
.dtbl-dl{display:flex;gap:.5rem}\r
.dtbl-dl button,.dtbl-pager button{padding:.35rem .6rem;cursor:pointer;border:1px solid #e5e7eb;border-radius:6px;background:#f8fafc}\r
.dtbl-pager{display:flex;gap:.5rem;align-items:center;margin:.5rem 0}\r
.dtbl-page-label{min-width:7.5rem;text-align:center} */\r
\r
/* barre */\r
.dtbl-toolbar {\r
    display: flex;\r
    align-items: center;\r
}\r
.dtbl-btn.dtbl-btn-icon { display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px; border:1px solid #e5e7eb; border-radius:6px; background:#fff; cursor:pointer; }\r
.dtbl-btn.dtbl-btn-icon:hover { background:#f8fafc; }\r
\r
/* popup contenu */\r
.dtbl-dl__stats { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px 12px; margin-bottom:12px; font-size:.9rem; border: solid 3px #f8fafc; padding: 8px;}\r
.dtbl-dl__scope { display:flex; gap:16px; align-items:center; margin:10px 0 14px 6px; flex-wrap:wrap; }\r
.dtbl-dl__legend { font-weight:600; margin-right:6px; }\r
.dtbl-dl__actions { display:flex; flex-wrap:wrap; gap:8px; }\r
.dtbl-dl__btn, .dtbl-page-prev, .dtbl-page-next { padding:6px 12px; border:1px solid #e5e7eb; background:#fff; border-radius:6px; cursor:pointer; display: flex; align-items: center; gap: 6px;}\r
.dtbl-dl__btn:hover, .dtbl-page-prev:not([disabled]):hover, .dtbl-page-next:not([disabled]):hover { background:#f3f4f6; }\r
.dtbl-page-prev[disabled], .dtbl-page-next[disabled] {cursor: default;}\r
\r
.dtbl-dl__btn.btn-csv { color:#2e7d32; }\r
.dtbl-dl__btn.btn-tsv { color:#388e3c; }\r
.dtbl-dl__btn.btn-json{ color:#ef6c00; }\r
.dtbl-dl__btn.btn-md  { color:#1565c0; }\r
.dtbl-dl__btn.btn-copy{ color:#6a1b9a; }\r
\r
.dtbl-pager {\r
    display: flex;\r
    gap: 6px;\r
    margin: 12px 0;\r
    align-items: center;\r
}\r
\r
th .dtbl-sort{ margin-left:6px; font-size:.9em; opacity:.75; width: 18px; height: 18px; display: inline-flex; align-items: center; justify-content: center;}\r
th.is-sorted .dtbl-sort{ opacity:1; }\r
th .dtbl-sort-idx{\r
  margin-left:4px; font-size:.7em; vertical-align:super; opacity:.85;\r
  padding:0 .25em; border-radius:6px; background:rgba(212, 210, 210, 0.06);\r
}\r
\r
:root{\r
    --dtbl-row-even: #F5F5F5;\r
    --dtbl-row-odd:  #fff;\r
}\r
\r
\r
.dtbl tbody tr.dtbl-row-odd  { background: var(--dtbl-row-odd); }\r
.dtbl tbody tr.dtbl-row-even { background: var(--dtbl-row-even); }\r
\r
\r
.table-1 {\r
    border-collapse: collapse;\r
    width: 100%;\r
    font-size: 14px;\r
    color: #999999;\r
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;\r
}\r
\r
.table-1 td {\r
    padding: 8px 12px;\r
    text-align: center;\r
}\r
\r
.table-1 thead > tr:nth-child(1) th:not(.outside):first-of-type {\r
    border-radius: 8px 0 0 0;\r
}\r
\r
.table-1 thead > tr:nth-child(1) th:not(.outside):last-of-type,\r
.table-1 thead > tr:has(> th:last-child.outside) > th:nth-last-child(2) {\r
    border-radius: 0 8px 0 0;\r
}\r
\r
.table-1 th:not(.outside) {\r
    background-color: #36304A;\r
    font-weight: 400;\r
    color: #f4f1f6;\r
    text-align: center;\r
    padding: 4px 12px;\r
    min-width: max-content;\r
    border-bottom: solid 1px #c1b8c7;\r
}\r
\r
.table-1 tbody tr:hover td:not(.outside) {\r
    color: #292929;\r
}\r
\r
.table-1 td {\r
    white-space: nowrap;\r
}\r
\r
.table-1.static td {\r
    border: solid 1px #d9d9d9;\r
    color: #292929 !important;\r
}\r
\r
.table-1 .outside {\r
    background-color: var(--background-color);\r
    border: none;\r
    width: fit-content;\r
    cursor: default;\r
}\r
\r
.table-1 th .dtbl-sort { display:inline-block; width:1.2em; text-align:center; margin-left:6px; opacity:.75; }\r
.table-1 th.is-sorted .dtbl-sort { opacity:1; }\r
.table-1 th .dtbl-sort-idx{\r
  display:inline-block; min-width:1.1em; margin-left:4px; font-size:.9em; vertical-align:super;\r
  padding:0 .35em; border-radius:6px; background:#fff; color: #000000; position: absolute;\r
}\r
`;var L=class{static reg=new Map;static inited=!1;static uid(){return"dt_"+Math.random().toString(36).slice(2,8)+Date.now().toString(36)}static init(){this.inited||(this.inited=!0,document.addEventListener("input",t=>{let e=t.target.closest("[data-dtbl-id]");if(!e)return;let s=this.reg.get(e.dataset.dtblId);s&&s._dispatch_input(t)}),document.addEventListener("click",t=>{let e=t.target.closest("[data-dtbl-id]");if(!e)return;let s=this.reg.get(e.dataset.dtblId);s&&s._dispatch_click(t)}))}};var O=class{constructor({locale:t}={}){this.collator=new Intl.Collator(t,{numeric:!0,sensitivity:"base"}),this.formatters=new Map,this._columns=[],this._rows=[],this._view_rows=[],this._sort_state=[],this._query="",this._page_size=null,this._page=1}get_columns(){return JSON.parse(JSON.stringify(this._columns))}set_columns(t){return this._columns=this._norm_cols(t||[]),this}update_column(t,e={}){let s=this.flat_columns().find(o=>o.id===t);if(!s)throw new Error(`TableState.update_column: unknown column "${t}"`);return Object.assign(s,e),this}set_columns_meta(t={}){let e=this.flat_columns();for(let[s,o]of Object.entries(t)){let i=e.find(n=>n.id===s);i&&Object.assign(i,o)}return this}flat_columns(){let t=[];return(function e(s){s.forEach(o=>o.children?e(o.children):t.push(o))})(this._columns),t}get_flat_columns(){return this.flat_columns().map(e=>({id:e.id,label:e.label,type:e.type,sortable:e.sortable===!0,width:e.width,align:e.align,searchable:e.searchable===!0}))}header_depth(){let t=e=>Math.max(0,...e.map(s=>s.children?1+t(s.children):1));return t(this._columns)}leaf_count(t){return t.children?t.children.reduce((e,s)=>e+this.leaf_count(s),0):1}set_rows(t){return this._rows=Array.isArray(t)?t.slice():[],this}add_rows(t=[]){return Array.isArray(t)||(t=[t]),this._rows.push(...t),this}clear_rows(){return this._rows.length=0,this}update_row_at(t,e={}){if(t<0||t>=this._rows.length)throw new Error("TableState.update_row_at: index out of range");return Object.assign(this._rows[t],e),this}set_cell_at(t,e,s){if(t<0||t>=this._rows.length)throw new Error("TableState.set_cell_at: index out of range");return(this._rows[t]??={})[e]=s,this}get_rows(t="view"){if(this.apply(),t==="raw")return this._rows.slice();if(t==="view")return this._view_rows.slice();if(t==="page")return this.page_slice().rows.slice();throw new Error(`TableState.get_rows: unknown scope "${t}"`)}set_query(t){return this._query=String(t||""),this}set_page_size(t){return this._page_size=t||null,this._page=1,this}set_page(t){return this._page=Math.max(1,parseInt(t||1,10)),this}sort_by(t,e=!0,s=!1){return s||(this._sort_state=[]),this._sort_state.push({key:t,asc:e}),this}set_sort(t=[]){return this._sort_state=Array.isArray(t)?t.filter(e=>e&&e.key):[],this}clear_sort(){return this._sort_state=[],this}apply(){let t=this._query.toLowerCase(),e=this.flat_columns(),s=e.filter(o=>o.searchable===!0);if(t?s.length===0?this._view_rows=[]:this._view_rows=this._rows.filter(o=>s.some(i=>String(o[i.id]??"").toLowerCase().includes(t))):this._view_rows=this._rows.slice(),this._sort_state.length){let o=this._view_rows.map((n,a)=>({row:n,idx:a})),i=n=>e.find(a=>a.id===n)?.type||"text";o.sort((n,a)=>{for(let r of this._sort_state){let l=i(r.key),c=n.row[r.key],_=a.row[r.key],h=this._compare_values(l,c,_);if(h)return r.asc?h:-h}return n.idx-a.idx}),this._view_rows=o.map(n=>n.row)}return this}page_slice(){if(!this._page_size)return{rows:this._view_rows,page:1,total_pages:1};let t=Math.max(1,Math.ceil(this._view_rows.length/this._page_size));this._page>t&&(this._page=t);let e=(this._page-1)*this._page_size;return{rows:this._view_rows.slice(e,e+this._page_size),page:this._page,total_pages:t}}format(t,e){return this.formatters.set(t,e),this}get sort_state(){return this._sort_state}get page_size(){return this._page_size}get page(){return this._page}_norm_cols(t,e=0,s=null){return t.map(o=>({id:o.id,label:o.label??o.id,type:o.type||"text",sortable:o.sortable!==!1,searchable:o.searchable===!0,width:o.width||null,align:o.align||null,comparator:o.comparator||null,children:o.children?this._norm_cols(o.children,e+1,o):null,_depth:e,_parent:s}))}_compare_values(t,e,s){let o=e==null||e==="",i=s==null||s==="";if(o&&i)return 0;if(o)return 1;if(i)return-1;if(t==="number"){let n=Number(e),a=Number(s),r=Number.isFinite(n)?n:-1/0,l=Number.isFinite(a)?a:-1/0;return r-l}if(t==="date"){let n=this._coerce_date(e),a=this._coerce_date(s);return n-a}return this.collator.compare(String(e),String(s))}_coerce_date(t){if(t instanceof Date)return t.getTime();let e=Date.parse(t);return Number.isFinite(e)?e:-864e13}};var I=class{constructor(t){this.table=t}toolbar_html(){return`<div class="dtbl-toolbar">${this.table.plugins.map(t=>t.toolbar_html?.()||"").join("")}</div>`}table_html(){let t=this.table.model.apply(),e=t.flat_columns(),s=t.header_depth(),o=[];(function a(r,l=0,c){o[l]??=[],r.forEach(_=>{let h=!!_.children;o[l].push({label:_.label,id:h?null:_.id,colspan:h?c.leaf_count(_):1,rowspan:h?1:s-l,align:_.align,sortable:_.sortable!==!1}),h&&a(_.children,l+1,c)})})(t.columns,0,t);let i=t.page_slice(),n=`<table class="dtbl ${this.table.opts.sticky_header?"dtbl-sticky":""}"><thead>`;for(let a of o){n+="<tr>";for(let r of a){let l=[];r.colspan>1&&l.push(`colspan="${r.colspan}"`),r.rowspan>1&&l.push(`rowspan="${r.rowspan}"`),r.id&&l.push(`data-col-id="${r.id}"`),r.align&&l.push(`style="text-align:${r.align}"`),n+=`<th ${l.join(" ")}>${r.label}${r.id&&r.sortable?'<span class="dtbl-sort">\u2195</span>':""}</th>`}n+="</tr>"}n+="</thead><tbody>";for(let a of i.rows){n+="<tr>";for(let r of e){let l=a[r.id],c=this.table.model.formatters.get(r.id),_=c?c(l,a):l==null?"":String(l);n+=`<td${r.align?` style="text-align:${r.align}"`:""}>${_}</td>`}n+="</tr>"}return n+="</tbody></table>",n+=this.table.plugins.map(a=>a.footer_html?.(i)||"").join(""),n}};var B=class{constructor(t={}){this.id=L.uid(),this.opts={sticky_header:!0,locale:void 0,...t},this.mode="virtual",this.model=new O({locale:this.opts.locale}),this.renderer=new I(this),this.plugins=[],this._plugin_by_name=new Map,this._wrap=null,this._adopt_table=null,this._adopt_sort_state=null,this._adopt_page=null,L.reg.set(this.id,this),L.init()}};function ct(p){return class extends p{static plugins=Object.create(null);static _names=[];static register_plugin(e,s){let o=String(e).toLowerCase();this.plugins[o]=s,this._names.includes(o)||this._names.push(o);let i=o.replace(/(^|[_-])(\w)/g,(n,a,r)=>r.toUpperCase());Object.hasOwn(this,i)||Object.defineProperty(this,i,{value:s,enumerable:!0})}static plugin_names(){return[...this._names]}use(e,s){let o,i;if(typeof e=="string"){i=e.toLowerCase();let a=this.constructor.plugins[i];if(!a)throw new Error(`unknown plugin "${i}". Available: ${this.constructor.plugin_names().join(", ")||"none"}`);o=new a(s||{})}else o=e,i=(o?.name||o?.constructor?.name||"plugin").toString().toLowerCase();o.attach?.(this),this.plugins.push(o),this._plugin_by_name.set(i,o);let n=i.replace(/-+/g,"_");return Object.hasOwn(this,n)||Object.defineProperty(this,n,{value:o,enumerable:!0}),this._render_toolbar_dom?.(),this}}}function pt(p){return class extends p{get_columns(){return this.model.get_columns()}get_flat_columns(){return this.model.get_flat_columns()}set_columns(e,{render:s=!0}={}){return this.model.set_columns(e),this.mode==="virtual"?s&&this._render_virtual_body?.(!0):(this._apply_column_meta_to_thead?.(this.model.get_flat_columns()),s&&this._render_toolbar_dom?.()),this}update_column(e,s={},{render:o=!0}={}){if(this.model.update_column(e,s),this.mode==="virtual")o&&this._render_virtual_body?.(!0);else{let i=this.model.get_flat_columns().find(n=>n.id===e);this._apply_column_meta_to_thead?.({[e]:i})}return this}set_columns_meta(e={},{render:s=!0}={}){return this.model.set_columns_meta(e),this.mode==="virtual"?s&&this._render_virtual_body?.(!0):(this._apply_column_meta_to_thead?.(e),s&&this._render_toolbar_dom?.()),this}}}function ht(p){return class extends p{set_rows(e,{render:s=!0}={}){if(this.model.set_rows(e),this.mode==="virtual")s&&this._render_virtual_body?.(!1);else if(s){let o=this._wrap?.querySelector(".dtbl-search")?.value||"";this._adopt_filter?.(o)}return this}add_rows(e=[],{render:s=!0}={}){if(this.model.add_rows(e),this.mode==="virtual")s&&this._render_virtual_body?.(!1);else if(s){let o=this._wrap?.querySelector(".dtbl-search")?.value||"";this._adopt_filter?.(o)}return this}clear_rows(){return this.model.clear_rows(),this.mode==="virtual"?this._render_virtual_body?.(!1):this._adopt_filter?.(this._wrap?.querySelector(".dtbl-search")?.value||""),this}update_row_at(e,s={},{render:o=!1}={}){return this.model.update_row_at(e,s),o&&(this.mode==="virtual"?this._render_virtual_body?.(!1):this._adopt_filter?.(this._wrap?.querySelector(".dtbl-search")?.value||"")),this}set_cell_at(e,s,o,{render:i=!1}={}){return this.model.set_cell_at(e,s,o),i&&(this.mode==="virtual"?this._render_virtual_body?.(!1):this._adopt_filter?.(this._wrap?.querySelector(".dtbl-search")?.value||"")),this}get_rows(e="view"){return this.model.get_rows(e)}from_nested_dict(e,s="row"){let o=new Set;for(let n in e)Object.keys(e[n]||{}).forEach(a=>o.add(a));let i=[...o].map(n=>{let a={[s]:n};for(let r in e)a[r]=e[r]?.[n];return a});return this.set_rows(i)}format(e,s){return this.model.format(e,s),this}}}function ut(p){return class extends p{toString(){return`<div class="dtbl-wrap" data-dtbl-id="${this.id}">${this.renderer.toolbar_html()}${this.renderer.table_html()}</div>`}_render_virtual_body(e=!1){let s=document.querySelector(`[data-dtbl-id="${this.id}"]`);if(s){if(e&&s.querySelector("table")?.remove(),e)s.insertAdjacentHTML("beforeend",this.renderer.table_html());else{let o=s.querySelector("table");if(!o){s.insertAdjacentHTML("beforeend",this.renderer.table_html());return}let i=document.createElement("tbody"),n=this.model.apply(),{rows:a,page:r,total_pages:l}=n.page_slice(),c=n.flat_columns();for(let u of a){let b=document.createElement("tr");for(let m of c){let f=document.createElement("td");m.align&&(f.style.textAlign=m.align);let x=this.model.formatters.get(m.id),g=u[m.id];f.innerHTML=x?x(g,u):g==null?"":String(g),b.appendChild(f)}i.appendChild(b)}o.tBodies[0]?.replaceWith(i);let _=s.querySelector(".dtbl-page-label");_&&(_.textContent=`Page ${r} / ${l}`);let h=s.querySelector(".dtbl-page-prev"),d=s.querySelector(".dtbl-page-next");h&&(h.disabled=r<=1),d&&(d.disabled=r>=l)}this._update_sort_icons(),e&&this._lock_column_widths?.(),this._apply_zebra?.()}}_update_sort_icons(){let e=document.querySelector(`[data-dtbl-id="${this.id}"]`);if(!e)return;let s=e.querySelector("thead");if(!s)return;let o=Array.from(s.rows);if(!o.length)return;let i=o.length-1,n=[],a=(h,d,u)=>{(n[h]??=[])[d]=u};for(let h=0;h<o.length;h++){let d=0;for(let u of o[h].cells){let b=Math.max(1,u.colSpan||1),m=Math.max(1,u.rowSpan||1);for(;n[h]?.[d]!=null;)d++;let f=d,x=f+b-1;for(let g=h;g<h+m;g++)for(let w=f;w<=x;w++)a(g,w,u);d=x+1}}let r=(n[i]||[]).filter(Boolean),l=[];this.mode==="virtual"?l=(this.model.sort_state||[]).map(h=>({key:h.key,asc:h.asc})):l=(this._adopt_sort_state||[]).map(h=>{let d=r[h.index];return d?{key:d.dataset.colId,asc:h.asc}:null}).filter(Boolean);let c=l.length,_=h=>{let d=l.findIndex(u=>u.key===h);return d>=0?d+1:0};for(let h of r){let d=h.dataset.colId||"";if(h.dataset.sort!=="true"){h.querySelector(".dtbl-sort")?.remove(),h.querySelector(".dtbl-sort-idx")?.remove(),h.classList.remove("is-sorted"),h.removeAttribute("data-sort-order");continue}let u=h.querySelector(".dtbl-sort");u||(u=document.createElement("span"),u.className="dtbl-sort",h.appendChild(u));let b=null;if(this.mode==="virtual"){let x=(this.model.sort_state||[]).find(g=>g.key===d);b=x?x.asc:null}else{let x=r.indexOf(h),g=(this._adopt_sort_state||[]).find(w=>w.index===x);b=g?g.asc:null}u.textContent=b==null?"\u2195":b?"\u25B2":"\u25BC";let m=_(d),f=h.querySelector(".dtbl-sort-idx");m>0&&c>1?(f||(f=document.createElement("sup"),f.className="dtbl-sort-idx",h.appendChild(f)),f.textContent=String(m),h.classList.add("is-sorted"),h.dataset.sortOrder=String(m)):(f?.remove(),b==null?(h.classList.remove("is-sorted"),h.removeAttribute("data-sort-order")):(h.classList.add("is-sorted"),h.dataset.sortOrder="1"))}}_apply_zebra(){let s=(this._adopt_table||document.querySelector(`[data-dtbl-id="${this.id}"] table`))?.tBodies?.[0];if(!s)return;let o=0;for(let i of s.rows){let n=i.dataset.hidden==="true"||i.style.display==="none";i.classList.remove("dtbl-row-odd","dtbl-row-even"),!n&&(i.classList.add(o%2?"dtbl-row-even":"dtbl-row-odd"),o++)}}_lock_column_widths({include_icons:e=!0,extra_px:s=6}={}){let o=this._adopt_table||document.querySelector(`[data-dtbl-id="${this.id}"] table`);if(!o)return;let i=o.tHead||o.querySelector("thead");if(!i)return;let n=Array.from(i.rows);if(!n.length)return;let a=n.length-1,r=[],l=(u,b,m)=>{r[u]??=[],r[u][b]=m};for(let u=0;u<n.length;u++){let b=0;for(let m of n[u].cells){let f=Math.max(1,m.colSpan||1),x=Math.max(1,m.rowSpan||1);for(;r[u]?.[b]!=null;)b++;let g=b,w=g+f-1;for(let k=u;k<u+x;k++)for(let $=g;$<=w;$++)l(k,$,m);b=w+1}}let c=(r[a]||[]).filter(Boolean),_=u=>{let b=Math.ceil(Math.max(u.scrollWidth||0,u.getBoundingClientRect().width||0));if(!e)return b+s;let m=0,f=x=>{if(!x)return;let g=getComputedStyle(x),w=g.position;if(w==="absolute"||w==="fixed"){let k=x.getBoundingClientRect(),$=parseFloat(g.marginLeft)||0,gt=parseFloat(g.marginRight)||0;m+=Math.ceil(k.width+$+gt)}};return f(u.querySelector(".dtbl-sort")),f(u.querySelector(".dtbl-sort-idx")),b+m+s},h=c.map(_),d=o.querySelector("colgroup[data-dtbl-colgroup]");for(d||(d=document.createElement("colgroup"),d.setAttribute("data-dtbl-colgroup","true"),o.insertBefore(d,o.firstChild));d.children.length<h.length;)d.appendChild(document.createElement("col"));for(;d.children.length>h.length;)d.removeChild(d.lastChild);h.forEach((u,b)=>{d.children[b].style.width=`${u}px`}),o.style.tableLayout="fixed"}_render_toolbar_dom(){let e=this._wrap||this._adopt_table?.closest(".dtbl-wrap");if(!e)return;e.querySelector(".dtbl-toolbar")?.remove();let s=document.createElement("div");s.innerHTML=`<div class="dtbl-toolbar">${this.plugins.map(a=>a.toolbar_html?.()||"").join("")}</div>`,e.prepend(s.firstChild),e.querySelector(".dtbl-pager")?.remove();let i=this.model.apply().page_slice(),n=this.plugins.map(a=>a.footer_html?.(i)||"").join("");n&&e.insertAdjacentHTML("beforeend",n)}_dispatch_input(e){for(let s of this.plugins)s.handle_input?.(e)}_dispatch_click(e){for(let s of this.plugins)s.handle_click?.(e)}}}function _t(p){return class extends p{static enhance(e,s={}){let o=new this(s);o.mode="adopt";let i=typeof e=="string"?document.querySelector(e):e;if(!i||i.tagName!=="TABLE")throw new Error("enhance: provide <table>");o._adopt_table=i,i.classList.add("dtbl"),o.opts.sticky_header&&i.classList.add("dtbl-sticky"),o._ingest_columns_from_thead(i.tHead||i.querySelector("thead"));let n=document.createElement("div");return n.className="dtbl-wrap",n.dataset.dtblId=o.id,i.parentNode.insertBefore(n,i),n.appendChild(i),o._wrap=n,o._render_toolbar_dom?.(),o._update_sort_icons?.(),o._lock_column_widths?.(),o}static _slug(e){let s=String(e||"").trim().toLowerCase().replace(/[^\p{L}\p{N}]+/gu,"_").replace(/^_+|_+$/g,"");return s?/\d/.test(s[0])?`c_${s}`:s:"col"}_ingest_columns_from_thead(e){let s=Array.from(e?.rows||[]);if(!s.length)return;let o=[],i=s.map(()=>[]),n=(d,u,b)=>{o[d]??=[],o[d][u]=b};for(let d=0;d<s.length;d++){let u=0;for(let b of s[d].cells){let m=Math.max(1,b.colSpan||1),f=Math.max(1,b.rowSpan||1);for(;o[d]?.[u]!=null;)u++;let x=u,g=x+m-1;for(let w=d;w<d+f;w++)for(let k=x;k<=g;k++)n(w,k,b);i[d].push({th:b,row:d,col_start:x,col_end:g,row_span:f,col_span:m}),u=g+1}}let a=s.length-1,r=d=>String(d??"").trim().toLowerCase()==="true",l=(d,u)=>{let b=(d.textContent||"").trim()||u,m=(d.dataset.colId||"").trim();m||(m=this.constructor._slug(b),d.dataset.colId=m);let f=r(d.dataset.sort),x=d.style.textAlign&&/^(left|center|right)$/.test(d.style.textAlign)?d.style.textAlign:null,g=r(d.dataset.search);return{id:m,label:b,sortable:f,align:x,searchable:g}},c=d=>{d.children?d.children.forEach(c):d.searchable=!0},_=d=>{let u=d.row+d.row_span,b=[];if(u<=a)for(let m of i[u])m.col_start>=d.col_start&&m.col_end<=d.col_end&&b.push(_(m));if(b.length){let m=l(d.th,`Group ${d.row}:${d.col_start}`),f={label:m.label,children:b};return m.searchable&&c(f),f}else{let{id:m,label:f,sortable:x,align:g,searchable:w}=l(d.th,`Col ${d.row}:${d.col_start}`);return{id:m,label:f,sortable:x,align:g,searchable:w}}},h=i[0].map(_);this.model.set_columns(h),this._adopt_cache_searchable_indexes_from_model()}_adopt_cache_searchable_indexes_from_model(){let e=this.model.get_flat_columns(),s=[];for(let o=0;o<e.length;o++)e[o]?.searchable===!0&&s.push(o);this._adopt_search_cols=s}_adopt_cache_searchable_indexes(e){let s=e?.rows?.[e.rows.length-1];if(!s){this._adopt_search_cols=null;return}let o=[];Array.from(s.cells).forEach((i,n)=>{i.dataset.search==="true"&&o.push(n)}),this._adopt_search_cols=o}_apply_column_meta_to_thead(e){if(!this._adopt_table)return;let s=this._adopt_table.tHead||this._adopt_table.querySelector("thead");if(!s)return;let o=s.rows[s.rows.length-1];if(!o)return;let i=Array.isArray(e)?Object.fromEntries(e.filter(n=>n&&n.id).map(n=>[n.id,n])):e;for(let n of o.cells){let a=(n.dataset.colId||"").trim();if(!a||!i[a])continue;let r=i[a];if(r.label!=null){let l=n.querySelector(".dtbl-sort");n.textContent=String(r.label),l&&n.appendChild(l)}if(r.align&&(n.style.textAlign=r.align),r.sortable!=null){n.dataset.sort=r.sortable?"true":"false";let l=n.querySelector(".dtbl-sort");r.sortable?l||(l=document.createElement("span"),l.className="dtbl-sort",l.textContent="\u2195",n.appendChild(l)):l?.remove()}r.searchable!=null&&(n.dataset.search=r.searchable?"true":"false")}this._adopt_cache_searchable_indexes_from_model(),this._update_sort_icons?.()}_adopt_filter(e){let s=this._adopt_table.tBodies[0],o=(e||"").toLowerCase();this._adopt_search_cols||this._adopt_cache_searchable_indexes_from_model();let i=this._adopt_search_cols||[];for(let n of s.rows){let a=o==="";if(!a)for(let r=0;r<i.length;r++){let l=i[r],c=n.cells[l];if(c&&c.textContent.toLowerCase().includes(o)){a=!0;break}}n.dataset.hidden=a?"false":"true",n.style.display=a?"":"none"}this._adopt_page!=null&&this._apply_adopt_pagination(),this._apply_zebra?.()}_adopt_sort(e,s,{new_first:o=!0,tri_state:i=!0,alt_clears_all:n=!1,alt:a=!1}={}){if(!e||e.dataset.sort!=="true")return;this._adopt_sort_state??=[];let r=[...e.parentNode.children].indexOf(e);if(n&&a){this._adopt_sort_state=[],this._apply_adopt_sort_to_dom();return}let l=this._adopt_sort_state.findIndex(c=>c.index===r);if(!s)l<0?this._adopt_sort_state=[{index:r,asc:!0}]:i&&this._adopt_sort_state[l].asc?this._adopt_sort_state=[{index:r,asc:!1}]:this._adopt_sort_state=[];else if(l<0){let c={index:r,asc:!0};o?this._adopt_sort_state.unshift(c):this._adopt_sort_state.push(c)}else{let c=this._adopt_sort_state[l];if(i&&c.asc?this._adopt_sort_state[l]={index:r,asc:!1}:this._adopt_sort_state.splice(l,1),o&&l!==0&&l<this._adopt_sort_state.length){let[_]=this._adopt_sort_state.splice(l,1);this._adopt_sort_state.unshift(_)}}this._apply_adopt_sort_to_dom()}_apply_adopt_sort_to_dom(){let e=this._adopt_table?.tBodies?.[0];if(!e)return;let s=[...e.rows],o=s.filter(a=>a.dataset.hidden!=="true"),i=s.filter(a=>a.dataset.hidden==="true");if(!this._adopt_sort_state.length)return;let n=this.model.collator;o.sort((a,r)=>{for(let l of this._adopt_sort_state){let c=a.cells[l.index]?.textContent.trim()??"",_=r.cells[l.index]?.textContent.trim()??"",h=parseFloat(c),d=parseFloat(_),u=!Number.isNaN(h)&&!Number.isNaN(d)?h-d:n.compare(c,_);if(u)return l.asc?u:-u}return 0}),e.replaceChildren(...o,...i),this._adopt_page!=null&&this._apply_adopt_pagination(),this._apply_zebra?.()}_adopt_page_info(){let e=[...this._adopt_table.tBodies[0].rows].filter(o=>o.dataset.hidden!=="true"),s=this.model.page_size||e.length;return{total_pages:Math.max(1,Math.ceil(e.length/s))}}_apply_adopt_pagination(){let s=[...this._adopt_table.tBodies[0].rows].filter(l=>l.dataset.hidden!=="true"),o=this.model.page_size||s.length,i=Math.max(1,Math.ceil(s.length/o));this._adopt_page=Math.max(1,Math.min(i,this._adopt_page||1)),s.forEach((l,c)=>{l.style.display=c>=(this._adopt_page-1)*o&&c<this._adopt_page*o?"":"none"});let n=this._wrap.querySelector(".dtbl-page-label");n&&(n.textContent=`Page ${this._adopt_page} / ${i}`);let a=this._wrap.querySelector(".dtbl-page-prev"),r=this._wrap.querySelector(".dtbl-page-next");a&&(a.disabled=this._adopt_page<=1),r&&(r.disabled=this._adopt_page>=i),this._apply_zebra?.()}}}function mt(p){return class extends p{to_csv(){if(this.mode==="adopt"){let l=[...this._adopt_table.tHead.querySelectorAll("tr:last-child th")].map(d=>d.textContent.trim()),_=[...this._adopt_table.tBodies[0].rows].filter(d=>d.dataset.hidden!=="true").map(d=>[...d.cells].map(u=>u.textContent.trim())),h=d=>(d=d==null?"":String(d),/[",\n]/.test(d)?`"${d.replace(/"/g,'""')}"`:d);return[l.map(h).join(","),..._.map(d=>d.map(h).join(","))].join(`
`)}let e=this.model.apply(),s=e.flat_columns(),{rows:o}=e.page_size?e.page_slice():{rows:e.view_rows.length?e.view_rows:e.rows},i=r=>(r=r==null?"":String(r),/[",\n]/.test(r)?`"${r.replace(/"/g,'""')}"`:r),n=s.map(r=>i(r.label)).join(","),a=o.map(r=>s.map(l=>i(e.formatters.get(l.id)?.(r[l.id],r)??r[l.id]??"")).join(",")).join(`
`);return`${n}
${a}`}to_json(){if(this.mode==="adopt"){let o=this._adopt_table.tBodies[0],i=[...this._adopt_table.tHead.querySelectorAll("tr:last-child th")].map((a,r)=>a.dataset.colId||a.textContent.trim()||`col${r+1}`),n=[...o.rows].filter(a=>a.dataset.hidden!=="true").map(a=>{let r={};return[...a.cells].forEach((l,c)=>r[i[c]]=l.textContent.trim()),r});return JSON.stringify(n,null,2)}let e=this.model.apply(),{rows:s}=e.page_size?e.page_slice():{rows:e.view_rows.length?e.view_rows:e.rows};return JSON.stringify(s,null,2)}static _download_blob(e,s,o){let i=new Blob([e],{type:o}),n=document.createElement("a");n.href=URL.createObjectURL(i),n.download=s,n.click(),setTimeout(()=>URL.revokeObjectURL(n.href),0)}}}var v=class{attach(t){return this.table=t,this}toolbar_html(){return""}footer_html(){return""}handle_input(t){}handle_click(t){}};var R=class extends v{constructor({placeholder:t="Search\u2026",debounce_ms:e=120}={}){super(),this.placeholder=t,this.debounce_ms=e}toolbar_html(){return`<input type="search" class="dtbl-search form-input" placeholder="${this.placeholder}">`}handle_input(t){t.target.matches(".dtbl-search")&&(clearTimeout(this._t),this._t=setTimeout(()=>{let e=t.target.value||"";this.table.mode==="virtual"?(this.table.model.set_query(e),this.table._render_virtual_body()):this.table._adopt_filter(e)},this.debounce_ms))}};var D=class extends v{constructor({multi:t=!0,require_modifier:e=!1,new_first:s=!0,alt_clears_all:o=!1}={}){super(),this.multi=t,this.require_modifier=e,this.new_first=s,this.alt_clears_all=o}handle_click(t){let e=t.target.closest("th[data-col-id]");if(!e||e.dataset.sort!=="true")return;let s=this.multi&&(!this.require_modifier||t.shiftKey||t.metaKey||t.ctrlKey),o=e.dataset.colId;if(this.table.mode==="virtual"){if(this.alt_clears_all&&t.altKey){this.table.model.set_sort([]),this.table._render_virtual_body(),this.table._update_sort_icons?.();return}let i=this._cycle_state(this.table.model.sort_state,o,s,this.new_first);this.table.model.set_sort(i),this.table._render_virtual_body(),this.table._update_sort_icons?.()}else this.table._adopt_sort(e,s,{new_first:this.new_first,tri_state:!0,alt_clears_all:this.alt_clears_all,alt:t.altKey}),this.table._update_sort_icons?.()}_cycle_state(t,e,s,o){let i=t.slice(),n=i.findIndex(a=>a.key===e);if(!s)return n<0?[{key:e,asc:!0}]:i[n].asc?(i[n]={key:e,asc:!1},i):(i.splice(n,1),i);if(n<0){let a={key:e,asc:!0};return o?i.unshift(a):i.push(a),i}if(i[n].asc?i[n]={key:e,asc:!1}:i.splice(n,1),o&&n<i.length&&n!==0){let[a]=i.splice(n,1);i.unshift(a)}return i}};var H=class extends v{constructor({page_size:t=10}={}){super(),this.page_size=t}attach(t){return super.attach(t),t.model.set_page_size(this.page_size),t.mode!=="virtual"&&(t._adopt_page=1,t._apply_adopt_pagination?.()),this}toolbar_html(){return""}footer_html(){if(this.table.mode==="virtual"){let{page:t,total_pages:e}=this.table.model.apply().page_slice();return this._pager_html(t,e)}else{let{total_pages:t}=this.table._adopt_page_info(),e=Math.max(1,Math.min(t,this.table._adopt_page||1));return this._pager_html(e,t)}}handle_click(t){let e=t.target.closest(".dtbl-page-prev, .dtbl-page-next");if(!e||e.disabled)return;let s=e.classList.contains("dtbl-page-prev")?-1:1;if(this.table.mode==="virtual"){let{total_pages:o}=this.table.model.apply().page_slice(),i=this.table.model.page||1,n=Math.max(1,Math.min(o,i+s));this.table.model.set_page(n),this.table._render_virtual_body()}else{let{total_pages:o}=this.table._adopt_page_info(),i=this.table._adopt_page||1;this.table._adopt_page=Math.max(1,Math.min(o,i+s)),this.table._apply_adopt_pagination()}}_pager_html(t,e){let s=t<=1?"disabled":"",o=t>=e?"disabled":"";return`
      <div class="dtbl-pager">
        <button class="dtbl-page-prev" ${s} aria-label="Previous page">\u25C0</button>
        <span class="dtbl-page-label">Page ${t} / ${e}</span>
        <button class="dtbl-page-next" ${o} aria-label="Next page">\u25B6</button>
      </div>`}};var P=class extends v{constructor({filename:t="data",default_scope:e="filtered",key_source:s="label",json_key_source:o=null,path_sep:i=" / "}={}){super(),this.filename=t,this.default_scope=e,this.key_source=s,this.json_key_source=o||s,this.path_sep=i}attach(t){this.table=t}toolbar_html(){return`
      <button class="dtbl-btn dtbl-btn-icon dtbl-download" title="Export">
        <span class="material-symbols-outlined">file_download</span>
      </button>`}handle_click(t){t.target.closest(".dtbl-download")&&this._open_popup()}_open_popup(){let t="dl_"+Math.random().toString(36).slice(2,8),e=this._gather_info(),s=`
      <h2 class="title">Download</h2>
      <div id="${t}" class="dtbl-dl">
        <div class="dtbl-dl__stats">
          <div><b>Columns:</b> ${e.cols}</div>
          <div><b>Rows (all):</b> ${e.rows_all}</div>
          <div><b>Rows (filtered):</b> ${e.rows_filtered}</div>
          <div><b>Rows (page):</b> ${e.rows_page}</div>
        </div>
        <div class="dtbl-dl__scope">
          <div class="dtbl-dl__legend">Scope</div>
          <label><input type="radio" name="dl-scope" value="all"      ${this.default_scope==="all"?"checked":""}> All rows</label>
          <label><input type="radio" name="dl-scope" value="filtered" ${this.default_scope==="filtered"?"checked":""}> Filtered rows</label>
          <label><input type="radio" name="dl-scope" value="page"     ${this.default_scope==="page"?"checked":""}> Current page</label>
        </div>
        <div class="dtbl-dl__actions">
          <button class="dtbl-dl__btn btn-csv"  data-act="csv"><span class="material-symbols-outlined">table_chart</span> CSV</button>
          <button class="dtbl-dl__btn btn-tsv"  data-act="tsv"><span class="material-symbols-outlined">grid_on</span> TSV</button>
          <button class="dtbl-dl__btn btn-json" data-act="json"><span class="material-symbols-outlined">data_object</span> JSON</button>
          <button class="dtbl-dl__btn btn-md"   data-act="md"><span class="material-symbols-outlined">text_snippet</span> Markdown</button>
          <button class="dtbl-dl__btn btn-cpy"  data-act="copy"><span class="material-symbols-outlined">content_copy</span> Copy</button>
        </div>
      </div>`;new PopUp({title:"Export data",content:s,actions:[{label:"Close",role:"close"}]}).open();let o=document.getElementById(t);o&&o.addEventListener("click",i=>{let n=i.target.closest(".dtbl-dl__btn");if(!n)return;let a=o.querySelector('input[name="dl-scope"]:checked')?.value||this.default_scope,r=n.dataset.act;r==="csv"?this._export_csv(a):r==="tsv"?this._export_tsv(a):r==="json"?this._export_json(a):r==="md"?this._export_md(a):r==="copy"&&this._copy_csv(a)})}_gather_info(){let e=this.table.model.get_flat_columns().length;if(this.table.mode==="virtual")return{cols:e,rows_all:this.table.model.get_rows("raw").length,rows_filtered:this.table.model.get_rows("view").length,rows_page:this.table.model.get_rows("page").length};let s=this.table._adopt_table.tBodies[0],o=s.rows.length,i=[...s.rows].filter(a=>a.dataset.hidden!=="true").length,n=[...s.rows].filter(a=>a.dataset.hidden!=="true"&&a.style.display!=="none").length;return{cols:e,rows_all:o,rows_filtered:i,rows_page:n}}_export_csv(t){let{headers:e,values:s}=this._collect_flat(t,!0),o=this._to_delim(e,s,",");this._download(`${this.filename}.csv`,o,"text/csv;charset=utf-8")}_export_tsv(t){let{headers:e,values:s}=this._collect_flat(t,!0),o=this._to_delim(e,s,"	");this._download(`${this.filename}.tsv`,o,"text/tab-separated-values;charset=utf-8")}_export_md(t){let{headers:e,values:s}=this._collect_flat(t,!0),o=l=>String(l).replace(/\|/g,"\\|"),i=`| ${e.map(o).join(" | ")} |`,n=`| ${e.map(()=>"---").join(" | ")} |`,a=s.map(l=>`| ${l.map(c=>o(c)).join(" | ")} |`).join(`
`),r=`${i}
${n}
${a}
`;this._download(`${this.filename}.md`,r,"text/markdown;charset=utf-8")}async _copy_csv(t){let{headers:e,values:s}=this._collect_flat(t,!0),o=this._to_delim(e,s,",");try{await navigator.clipboard.writeText(o)}catch{let i=document.createElement("textarea");i.value=o,document.body.appendChild(i),i.select();try{document.execCommand("copy")}finally{i.remove()}}}_export_json(t){let{paths:e,values:s}=this._collect_for_json(t),o=s.map(n=>this._nest_row(e,n)),i=JSON.stringify(o,null,2);this._download(`${this.filename}.json`,i,"application/json;charset=utf-8")}_collect_flat(t,e){let s=this.table.model.get_columns(),o=this.table.model.get_flat_columns(),n=this._leaf_paths(s,this.key_source).map(c=>c.join(this.path_sep));if(this.table.mode==="virtual"){let c=this.table.model;c.apply();let _;t==="all"?_=c.get_rows("raw"):t==="filtered"?_=c.get_rows("view"):_=c.get_rows("page");let h=c.formatters,d=_.map(u=>o.map(b=>{let m=u[b.id];if(!e)return m;let f=h.get(b.id);return f?f(m,u):m??""}));return{headers:n,values:d}}let a=this.table._adopt_table.tBodies[0],r;t==="all"?r=[...a.rows]:t==="filtered"?r=[...a.rows].filter(c=>c.dataset.hidden!=="true"):r=[...a.rows].filter(c=>c.dataset.hidden!=="true"&&c.style.display!=="none");let l=r.map(c=>{let _=[...c.cells];return o.map((h,d)=>_[d]?.textContent?.trim()??"")});return{headers:n,values:l}}_collect_for_json(t){let e=this.table.model.get_columns(),s=this.table.model.get_flat_columns(),o=this._leaf_paths(e,this.json_key_source);if(this.table.mode==="virtual"){let r=this.table.model;r.apply();let l;t==="all"?l=r.get_rows("raw"):t==="filtered"?l=r.get_rows("view"):l=r.get_rows("page");let c=l.map(_=>s.map(h=>_[h.id]));return{paths:o,values:c}}let i=this.table._adopt_table.tBodies[0],n;t==="all"?n=[...i.rows]:t==="filtered"?n=[...i.rows].filter(r=>r.dataset.hidden!=="true"):n=[...i.rows].filter(r=>r.dataset.hidden!=="true"&&r.style.display!=="none");let a=n.map(r=>{let l=[...r.cells];return s.map((c,_)=>l[_]?.textContent?.trim()??"")});return{paths:o,values:a}}_leaf_paths(t,e){let s=[],o=n=>e==="id"?n.id??n.label??"col":n.label??n.id??"col",i=(n,a=[])=>{for(let r of n||[])if(r.children&&r.children.length){let l=e==="id"?r.id??r.label??"":r.label??r.id??"";i(r.children,l?[...a,l]:[...a])}else s.push([...a,o(r)])};return i(t,[]),s}_nest_row(t,e){let s={};for(let o=0;o<t.length;o++){let i=t[o],n=s;for(let r=0;r<i.length-1;r++){let l=i[r]??"";(!(l in n)||typeof n[l]!="object"||n[l]===null)&&(n[l]={}),n=n[l]}let a=i[i.length-1]??"value";n[a]=e[o]}return s}_to_delim(t,e,s){let o=a=>(a=a==null?"":String(a),/[\"\n,]/.test(a)?`"${a.replace(/"/g,'""')}"`:a),i=t.map(o).join(s),n=e.map(a=>a.map(r=>o(r)).join(s)).join(`
`);return`${i}
${n}`}_download(t,e,s){if(typeof this.table.constructor._download_blob=="function"){this.table.constructor._download_blob(e,t,s);return}let i=new Blob([e],{type:s}),n=document.createElement("a");n.href=URL.createObjectURL(i),n.download=t,n.click(),setTimeout(()=>URL.revokeObjectURL(n.href),0)}};y(dt,"webtool__table_css");var Y=class extends B{},G=class extends ct(Y){},Q=class extends pt(G){},Z=class extends ht(Q){},tt=class extends ut(Z){},et=class extends _t(tt){},S=class extends mt(et){};S.register_plugin("search",R);S.register_plugin("sort",D);S.register_plugin("pagination",H);S.register_plugin("downloads",P);var ot={};E(ot,{LoadingScreen:()=>U});var bt=`
#loading-screen.active {
    display: flex; /* visible */
}

#loading-screen {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(25, 25, 25, 0.8);
    color: #f3f3f3;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    padding: 20px;
    box-sizing: border-box;
    overflow-y: auto;
    max-height: 100vh;
}

.spinner {
    border: 8px solid #333; /* Light gray */
    border-top: 8px solid #f3f3f3; /* White */
    border-radius: 50%;
    width: 60px;
    height: 60px;
    animation: spin 1.5s linear infinite;
    margin-bottom: 1.5rem;
}

#loading-steps {
    width: 100%;
    max-width: 400px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.loading-step {
    background: rgba(255, 255, 255, 0.1);
    padding: 10px 15px;
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.loading-step-title {
    font-weight: 600;
    font-size: 1.1em;
    color: #eee;
}

.loading-step-progress {
    width: 100%;
    height: 14px;
    border-radius: 7px;
    overflow: hidden;
    -webkit-appearance: none;
    appearance: none;
}

.loading-step-progress::-webkit-progress-bar {
    background-color: #444;
    border-radius: 7px;
}

.loading-step-progress::-webkit-progress-value {
    background-color: #66bb6a; /* green */
    border-radius: 7px;
}

.loading-step-progress::-moz-progress-bar {
    background-color: #66bb6a;
    border-radius: 7px;
}

.loading-step-info {
    font-size: 0.9em;
    color: #ccc;
    min-height: 18px; /* reserve space */
    font-style: italic;
}

#loading-detail {
    margin-top: 20px;
    max-width: 400px;
    color: #ccc;
    font-size: 0.9em;
    font-family: monospace;
}

.loading-detail-item {
    margin-bottom: 4px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
`;var U=class{static ROOT_ID="loading-screen";static STEPS_ID="loading-steps";static DETAIL_ID="loading-detail";static#t;static#e;static#s;static#o(){if(this.#t&&document.body.contains(this.#t))return;let t=document.getElementById(this.ROOT_ID);if(!t){t=document.createElement("div"),t.id=this.ROOT_ID;let e=document.createElement("div");e.className="spinner",t.appendChild(e);let s=document.createElement("div");s.id=this.STEPS_ID,t.appendChild(s);let o=document.createElement("div");o.id=this.DETAIL_ID,t.appendChild(o),document.body?document.body.appendChild(t):window.addEventListener("DOMContentLoaded",()=>{document.body.appendChild(t)})}this.#t=t,this.#e=t.querySelector("#"+this.STEPS_ID),this.#s=t.querySelector("#"+this.DETAIL_ID)}static show(){this.#o(),this.#t.classList.add("active")}static hide(){this.#o(),this.#t.classList.remove("active")}static update(t={}){this.#o();let e=Array.isArray(t.main_steps)?t.main_steps:[],s=t.detail&&typeof t.detail=="object"?t.detail:{};this.#e&&this.#i(e),this.#s&&this.#n(s)}static#i(t){let e=this.#e,s=Array.from(e.querySelectorAll(".loading-step")),o=new Map(s.map(i=>[i.dataset.title||i.querySelector(".loading-step-title")?.textContent||"",i]));s.forEach(i=>{let n=i.dataset.title||i.querySelector(".loading-step-title")?.textContent||"";t.find(a=>a.title===n)||i.remove()}),t.forEach(i=>{let n=String(i.title??""),a=o.get(n);if(!a){a=document.createElement("div"),a.className="loading-step",a.dataset.title=n;let r=document.createElement("div");r.className="loading-step-title",a.appendChild(r);let l=document.createElement("progress");l.className="loading-step-progress",l.max=1,a.appendChild(l);let c=document.createElement("div");c.className="loading-step-info",a.appendChild(c),e.appendChild(a)}a.dataset.title=n,a.querySelector(".loading-step-title").textContent=n,a.querySelector(".loading-step-progress").value=Number(i.progress??0),a.querySelector(".loading-step-info").textContent=String(i.info??"")})}static#n(t){let e=this.#s;e.innerHTML="",Object.entries(t).forEach(([s,o])=>{let i=document.createElement("div");i.className="loading-detail-item",i.textContent=`${s}: ${o}`,e.appendChild(i)})}};y(bt,"webtool__loading_screen_css");var it={};E(it,{Toast:()=>F});var ft=`/* Container : stack bottom-right */
#toast-container {
  position: fixed;
  right: 20px;
  bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 9999;
  pointer-events: none;
}

/* Toast element */
.toast {
  pointer-events: auto;
  min-width: 200px;
  max-width: 400px;
  padding: 10px 14px;
  border-radius: 4px;
  border-left: 14px solid transparent; /* couleur dynamique */
  background: #f9fafb; /* fond neutre clair */
  color: #111827;      /* texte neutre fonc\xE9 */
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 0.9rem;
  font-weight: 500;
  box-shadow: 0 6px 18px rgba(0,0,0,0.12);
  opacity: 0;
  transform: translateX(22px);
  transition: opacity 0.25s ease, transform 0.25s ease;
}

/* Active = visible */
.toast.active {
  opacity: 1;
  transform: translateX(-12px);
}

/* Variants: border-left color only */
.toast.info {
  border-color: #1a9a9c; /* bleu */
  color: #1a9a9c;
}
.toast.success {
  border-color: #33982a; /* vert */
  color: #33982a;
}
.toast.warning {
  border-color: #b68c00; /* orange */
  color: #b68c00;
}
.toast.error {
  border-color: #cd0000; /* rouge */
  color: #cd0000;
}
`;var F=class{static type=Object.freeze({info:"info",success:"success",warning:"warning",error:"error"});static _ensure(){let t=document.getElementById("toast-container");return t||(t=document.createElement("div"),t.id="toast-container",document.body.appendChild(t)),t}static _make(t,e,s=3e3,o={}){let i=this._ensure(),n=document.createElement("div");n.className=`toast ${t}`,n.setAttribute("role","status"),n.setAttribute("aria-live","polite"),o.html?n.innerHTML=e:n.textContent=e,i.appendChild(n),requestAnimationFrame(()=>n.classList.add("active"));let a=()=>{n.classList.remove("active"),n.addEventListener("transitionend",()=>n.remove(),{once:!0})},r=setTimeout(a,s);return o.pauseOnHover&&n.addEventListener("mouseenter",()=>clearTimeout(r),{once:!0}),{el:n,close:a}}static clear(){let t=document.getElementById("toast-container");t&&(t.innerHTML="")}static info(t,e,s){return this._make(this.type.info,t,e,s)}static success(t,e,s){return this._make(this.type.success,t,e,s)}static warning(t,e,s){return this._make(this.type.warning,t,e,s)}static error(t,e,s){return this._make(this.type.error,t,e,s)}};y(ft,"webtool__toast_css");return kt(At);})();
//# sourceMappingURL=toolbox.bundle.js.map
