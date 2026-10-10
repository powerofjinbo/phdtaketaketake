(globalThis.TURBOPACK||(globalThis.TURBOPACK=[])).push(["object"==typeof document?document.currentScript:void 0,98183,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0});var n={assign:function(){return l},searchParamsToUrlQuery:function(){return i},urlQueryToSearchParams:function(){return s}};for(var o in n)Object.defineProperty(r,o,{enumerable:!0,get:n[o]});function i(e){let t={};for(let[r,n]of e.entries()){let e=t[r];void 0===e?t[r]=n:Array.isArray(e)?e.push(n):t[r]=[e,n]}return t}function a(e){return"string"==typeof e?e:("number"!=typeof e||isNaN(e))&&"boolean"!=typeof e?"":String(e)}function s(e){let t=new URLSearchParams;for(let[r,n]of Object.entries(e))if(Array.isArray(n))for(let e of n)t.append(r,a(e));else t.set(r,a(n));return t}function l(e,...t){for(let r of t){for(let t of r.keys())e.delete(t);for(let[t,n]of r.entries())e.append(t,n)}return e}},18967,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0});var n={DecodeError:function(){return m},MiddlewareNotFoundError:function(){return b},MissingStaticPage:function(){return w},NormalizeError:function(){return x},PageNotFoundError:function(){return y},SP:function(){return v},ST:function(){return g},WEB_VITALS:function(){return i},execOnce:function(){return a},getDisplayName:function(){return f},getLocationOrigin:function(){return c},getURL:function(){return u},isAbsoluteUrl:function(){return l},isResSent:function(){return d},loadGetInitialProps:function(){return p},normalizeRepeatedSlashes:function(){return h},stringifyError:function(){return j}};for(var o in n)Object.defineProperty(r,o,{enumerable:!0,get:n[o]});let i=["CLS","FCP","FID","INP","LCP","TTFB"];function a(e){let t,r=!1;return(...n)=>(r||(r=!0,t=e(...n)),t)}let s=/^[a-zA-Z][a-zA-Z\d+\-.]*?:/,l=e=>s.test(e);function c(){let{protocol:e,hostname:t,port:r}=window.location;return`${e}//${t}${r?":"+r:""}`}function u(){let{href:e}=window.location,t=c();return e.substring(t.length)}function f(e){return"string"==typeof e?e:e.displayName||e.name||"Unknown"}function d(e){return e.finished||e.headersSent}function h(e){let t=e.split("?");return t[0].replace(/\\/g,"/").replace(/\/\/+/g,"/")+(t[1]?`?${t.slice(1).join("?")}`:"")}async function p(e,t){let r=t.res||t.ctx&&t.ctx.res;if(!e.getInitialProps)return t.ctx&&t.Component?{pageProps:await p(t.Component,t.ctx)}:{};let n=await e.getInitialProps(t);if(r&&d(r))return n;if(!n)throw Object.defineProperty(Error(`"${f(e)}.getInitialProps()" should resolve to an object. But found "${n}" instead.`),"__NEXT_ERROR_CODE",{value:"E1025",enumerable:!1,configurable:!0});return n}let v="u">typeof performance,g=v&&["mark","measure","getEntriesByName"].every(e=>"function"==typeof performance[e]);class m extends Error{}class x extends Error{}class y extends Error{constructor(e){super(),this.code="ENOENT",this.name="PageNotFoundError",this.message=`Cannot find module for page: ${e}`}}class w extends Error{constructor(e,t){super(),this.message=`Failed to load static file for page: ${e} ${t}`}}class b extends Error{constructor(){super(),this.code="ENOENT",this.message="Cannot find the middleware module"}}function j(e){return JSON.stringify({message:e.message,stack:e.stack})}},33525,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"warnOnce",{enumerable:!0,get:function(){return n}});let n=e=>{}},95057,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0});var n={formatUrl:function(){return s},formatWithValidation:function(){return c},urlObjectKeys:function(){return l}};for(var o in n)Object.defineProperty(r,o,{enumerable:!0,get:n[o]});let i=e.r(90809)._(e.r(98183)),a=/https?|ftp|gopher|file/;function s(e){let{auth:t,hostname:r}=e,n=e.protocol||"",o=e.pathname||"",s=e.hash||"",l=e.query||"",c=!1;t=t?encodeURIComponent(t).replace(/%3A/i,":")+"@":"",e.host?c=t+e.host:r&&(c=t+(~r.indexOf(":")?`[${r}]`:r),e.port&&(c+=":"+e.port)),l&&"object"==typeof l&&(l=String(i.urlQueryToSearchParams(l)));let u=e.search||l&&`?${l}`||"";return n&&!n.endsWith(":")&&(n+=":"),e.slashes||(!n||a.test(n))&&!1!==c?(c="//"+(c||""),o&&"/"!==o[0]&&(o="/"+o)):c||(c=""),s&&"#"!==s[0]&&(s="#"+s),u&&"?"!==u[0]&&(u="?"+u),o=o.replace(/[?#]/g,encodeURIComponent),u=u.replace("#","%23"),`${n}${c}${o}${u}${s}`}let l=["auth","hash","host","hostname","href","path","pathname","port","protocol","query","search","slashes"];function c(e){return s(e)}},18581,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"useMergedRef",{enumerable:!0,get:function(){return o}});let n=e.r(71645);function o(e,t){let r=(0,n.useRef)(null),o=(0,n.useRef)(null);return(0,n.useCallback)(n=>{if(null===n){let e=r.current;e&&(r.current=null,e());let t=o.current;t&&(o.current=null,t())}else e&&(r.current=i(e,n)),t&&(o.current=i(t,n))},[e,t])}function i(e,t){if("function"!=typeof e)return e.current=t,()=>{e.current=null};{let r=e(t);return"function"==typeof r?r:()=>e(null)}}("function"==typeof r.default||"object"==typeof r.default&&null!==r.default)&&void 0===r.default.__esModule&&(Object.defineProperty(r.default,"__esModule",{value:!0}),Object.assign(r.default,r),t.exports=r.default)},73668,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"isLocalURL",{enumerable:!0,get:function(){return i}});let n=e.r(18967),o=e.r(52817);function i(e){if(!(0,n.isAbsoluteUrl)(e))return!0;try{let t=(0,n.getLocationOrigin)(),r=new URL(e,t);return r.origin===t&&(0,o.hasBasePath)(r.pathname)}catch(e){return!1}}},84508,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"errorOnce",{enumerable:!0,get:function(){return n}});let n=e=>{}},22016,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0});var n={default:function(){return m},useLinkStatus:function(){return y}};for(var o in n)Object.defineProperty(r,o,{enumerable:!0,get:n[o]});let i=e.r(90809),a=e.r(43476),s=i._(e.r(71645)),l=e.r(95057),c=e.r(8372),u=e.r(18581),f=e.r(18967),d=e.r(5550);e.r(33525);let h=e.r(88540),p=e.r(91949),v=e.r(73668),g=e.r(9396);function m(t){var r,n;let o,i,m,[y,w]=(0,s.useOptimistic)(p.IDLE_LINK_STATUS),b=(0,s.useRef)(null),{href:j,as:M,children:P,prefetch:k=null,passHref:E,replace:S,shallow:N,scroll:_,onClick:I,onMouseEnter:L,onTouchStart:C,legacyBehavior:R=!1,onNavigate:T,transitionTypes:O,ref:A,unstable_dynamicOnHover:z,...U}=t;o=P,R&&("string"==typeof o||"number"==typeof o)&&(o=(0,a.jsx)("a",{children:o}));let D=s.default.useContext(c.AppRouterContext),$=!1!==k,F=!1!==k?null===(n=k)||"auto"===n?g.FetchStrategy.PPR:g.FetchStrategy.Full:g.FetchStrategy.PPR,B="string"==typeof(r=M||j)?r:(0,l.formatUrl)(r);if(R){if(o?.$$typeof===Symbol.for("react.lazy"))throw Object.defineProperty(Error("`<Link legacyBehavior>` received a direct child that is either a Server Component, or JSX that was loaded with React.lazy(). This is not supported. Either remove legacyBehavior, or make the direct child a Client Component that renders the Link's `<a>` tag."),"__NEXT_ERROR_CODE",{value:"E863",enumerable:!1,configurable:!0});i=s.default.Children.only(o)}let K=R?i&&"object"==typeof i&&i.ref:A,V=s.default.useCallback(e=>(null!==D&&(b.current=(0,p.mountLinkInstance)(e,B,D,F,$,w)),()=>{b.current&&((0,p.unmountLinkForCurrentNavigation)(b.current),b.current=null),(0,p.unmountPrefetchableInstance)(e)}),[$,B,D,F,w]),W={ref:(0,u.useMergedRef)(V,K),onClick(t){R||"function"!=typeof I||I(t),R&&i.props&&"function"==typeof i.props.onClick&&i.props.onClick(t),!D||t.defaultPrevented||function(t,r,n,o,i,a,l){if("u">typeof window){let c,{nodeName:u}=t.currentTarget;if("A"===u.toUpperCase()&&((c=t.currentTarget.getAttribute("target"))&&"_self"!==c||t.metaKey||t.ctrlKey||t.shiftKey||t.altKey||t.nativeEvent&&2===t.nativeEvent.which)||t.currentTarget.hasAttribute("download"))return;if(!(0,v.isLocalURL)(r)){o&&(t.preventDefault(),location.replace(r));return}if(t.preventDefault(),a){let e=!1;if(a({preventDefault:()=>{e=!0}}),e)return}let{dispatchNavigateAction:f}=e.r(99781);s.default.startTransition(()=>{f(r,o?"replace":"push",!1===i?h.ScrollBehavior.NoScroll:h.ScrollBehavior.Default,n.current,l)})}}(t,B,b,S,_,T,O)},onMouseEnter(e){R||"function"!=typeof L||L(e),R&&i.props&&"function"==typeof i.props.onMouseEnter&&i.props.onMouseEnter(e),D&&$&&(0,p.onNavigationIntent)(e.currentTarget,!0===z)},onTouchStart:function(e){R||"function"!=typeof C||C(e),R&&i.props&&"function"==typeof i.props.onTouchStart&&i.props.onTouchStart(e),D&&$&&(0,p.onNavigationIntent)(e.currentTarget,!0===z)}};return(0,f.isAbsoluteUrl)(B)?W.href=B:R&&!E&&("a"!==i.type||"href"in i.props)||(W.href=(0,d.addBasePath)(B)),m=R?s.default.cloneElement(i,W):(0,a.jsx)("a",{...U,...W,children:o}),(0,a.jsx)(x.Provider,{value:y,children:m})}e.r(84508);let x=(0,s.createContext)(p.IDLE_LINK_STATUS),y=()=>(0,s.useContext)(x);("function"==typeof r.default||"object"==typeof r.default&&null!==r.default)&&void 0===r.default.__esModule&&(Object.defineProperty(r.default,"__esModule",{value:!0}),Object.assign(r.default,r),t.exports=r.default)},4421,21101,e=>{"use strict";let t="phdtake:";function r(e,r){try{let n=localStorage.getItem(t+e);return n?JSON.parse(n):r}catch{return r}}function n(e,r){localStorage.setItem(t+e,JSON.stringify(r))}let o="phdtake:setup";function i(){window.dispatchEvent(new Event(o))}function a(){return r("run_tombstones",[])}function s(){var e;let t,o,{runs:i,changed:a}=(e=r("runs",[]),t=Date.now(),o=!1,{runs:e.map(e=>{var r;return("researching"===(r=e.status)||"scoring"===r)&&t-(e.updated_at??0)>18e4?(o=!0,{...e,status:"error",error:"This run was interrupted — the tab was closed or reloaded while it was running. Runs execute in your browser, so they can't continue in the background. Start a new run to try again.",progress_note:"interrupted"}):e}),changed:o});if(a)try{n("runs",i)}catch{}return i}let l=new Set,c=!1;function u(){l.forEach(e=>e())}e.s(["deleteRun",0,function(e){n("runs",r("runs",[]).filter(t=>t.id!==e));let t=a();t.includes(e)||n("run_tombstones",[...t,e].slice(-100)),u()},"getRun",0,function(e){return s().find(t=>t.id===e)||null},"loadProfile",0,function(){return r("profile",null)},"loadRuns",0,s,"loadSettings",0,function(){return r("settings",null)},"newRunId",0,function(){return`run_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,7)}`},"onRunsChanged",0,function(e){return l.add(e),c||(c=!0,window.addEventListener("storage",e=>{e.key===t+"runs"&&u()})),()=>l.delete(e)},"onSetupChanged",0,function(e){let r=r=>{(r.key===t+"settings"||r.key===t+"profile")&&e()};return window.addEventListener(o,e),window.addEventListener("storage",r),()=>{window.removeEventListener(o,e),window.removeEventListener("storage",r)}},"saveProfile",0,function(e){n("profile",e),i()},"saveSettings",0,function(e){n("settings",e),i()},"upsertRun",0,function(e){var t;if(t=e.id,a().includes(t))return;e.updated_at=Date.now();let o=r("runs",[]).filter(t=>t.id!==e.id);o.unshift(e);let i=o.slice(0,20);for(;;)try{n("runs",i);break}catch{let t=[...i].reverse().find(t=>t.id!==e.id&&null!==t.results);if(t){t.results=null,t.portfolio_summary="(results dropped to free browser storage — re-run to regenerate)";continue}if(i.length>1){i=i.filter((t,r)=>t.id===e.id||r<i.length-1);continue}break}u()}],4421);var f=e.i(43476);let d={viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:1.6,strokeLinecap:"round",strokeLinejoin:"round"};e.s(["IconArrow",0,({className:e="h-4 w-4"})=>(0,f.jsx)("svg",{...d,strokeWidth:1.8,className:e,children:(0,f.jsx)("path",{d:"M5 12h14M13 6l6 6-6 6"})}),"IconBook",0,({className:e="h-5 w-5"})=>(0,f.jsx)("svg",{...d,className:e,children:(0,f.jsx)("path",{d:"M4 5.5A1.5 1.5 0 015.5 4H11v15H5.5A1.5 1.5 0 004 20.5v-15zM20 5.5A1.5 1.5 0 0018.5 4H13v15h5.5a1.5 1.5 0 011.5 1.5v-15z"})}),"IconChart",0,({className:e="h-5 w-5"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("path",{d:"M4 20h16"}),(0,f.jsx)("path",{d:"M7 16v-5M12 16V6M17 16v-8"})]}),"IconCheck",0,({className:e="h-4 w-4"})=>(0,f.jsx)("svg",{...d,strokeWidth:2.2,className:e,children:(0,f.jsx)("path",{d:"M5 12.5l4.2 4L19 7"})}),"IconCompass",0,({className:e="h-5 w-5"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("circle",{cx:"12",cy:"12",r:"8.5"}),(0,f.jsx)("path",{d:"M15.5 8.5l-2 5-5 2 2-5 5-2z"})]}),"IconDoc",0,({className:e="h-5 w-5"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("path",{d:"M6 3h8l5 5v12a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1z"}),(0,f.jsx)("path",{d:"M14 3v5h5M8.5 13h7M8.5 16.5h4.5"})]}),"IconEye",0,({className:e="h-4 w-4",off:t=!1})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("path",{d:"M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"}),(0,f.jsx)("circle",{cx:"12",cy:"12",r:"2.8"}),t&&(0,f.jsx)("path",{d:"M4 4l16 16"})]}),"IconFlask",0,({className:e="h-5 w-5"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("path",{d:"M9.5 3h5M10 3v6L4.8 18.2A1.8 1.8 0 006.4 21h11.2a1.8 1.8 0 001.6-2.8L14 9V3"}),(0,f.jsx)("path",{d:"M7.5 15h9"})]}),"IconHeart",0,({className:e="h-4 w-4"})=>(0,f.jsx)("svg",{...d,className:e,children:(0,f.jsx)("path",{d:"M12 20s-7.5-4.4-7.5-10A4.3 4.3 0 0112 7.3 4.3 4.3 0 0119.5 10c0 5.6-7.5 10-7.5 10z"})}),"IconKey",0,({className:e="h-5 w-5"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("circle",{cx:"8",cy:"15",r:"4"}),(0,f.jsx)("path",{d:"M11 12l8-8M16 7l2.5 2.5M14 9l2 2"})]}),"IconNetwork",0,({className:e="h-5 w-5"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("circle",{cx:"12",cy:"12",r:"2.6"}),(0,f.jsx)("circle",{cx:"5",cy:"5.5",r:"1.8"}),(0,f.jsx)("circle",{cx:"19",cy:"5.5",r:"1.8"}),(0,f.jsx)("circle",{cx:"5",cy:"18.5",r:"1.8"}),(0,f.jsx)("circle",{cx:"19",cy:"18.5",r:"1.8"}),(0,f.jsx)("path",{d:"M6.4 6.8l3.6 3.4M17.6 6.8L14 10.2M6.4 17.2l3.6-3.4M17.6 17.2L14 13.8"})]}),"IconPlus",0,({className:e="h-4 w-4"})=>(0,f.jsx)("svg",{...d,strokeWidth:1.9,className:e,children:(0,f.jsx)("path",{d:"M12 5v14M5 12h14"})}),"IconShield",0,({className:e="h-5 w-5"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("path",{d:"M12 3l7 3v5.5c0 4.5-3 8-7 9.5-4-1.5-7-5-7-9.5V6l7-3z"}),(0,f.jsx)("path",{d:"M9 12l2.2 2.2L15.5 10"})]}),"IconSpark",0,({className:e="h-5 w-5"})=>(0,f.jsx)("svg",{...d,className:e,children:(0,f.jsx)("path",{d:"M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"})}),"IconTrash",0,({className:e="h-4 w-4"})=>(0,f.jsx)("svg",{...d,className:e,children:(0,f.jsx)("path",{d:"M4.5 7h15M9.5 7V4.5h5V7M6.5 7l.8 12.5h9.4L17.5 7"})}),"IconUpload",0,({className:e="h-6 w-6"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("path",{d:"M12 15V4M7.5 8.5L12 4l4.5 4.5"}),(0,f.jsx)("path",{d:"M4 15v3.5A1.5 1.5 0 005.5 20h13a1.5 1.5 0 001.5-1.5V15"})]}),"IconUser",0,({className:e="h-5 w-5"})=>(0,f.jsxs)("svg",{...d,className:e,children:[(0,f.jsx)("circle",{cx:"12",cy:"8",r:"3.6"}),(0,f.jsx)("path",{d:"M4.5 20c1.2-3.6 4-5.4 7.5-5.4s6.3 1.8 7.5 5.4"})]})],21101)},18566,(e,t,r)=>{t.exports=e.r(76562)},42724,e=>{"use strict";var t=e.i(43476),r=e.i(22016),n=e.i(18566),o=e.i(71645),i=e.i(4421),a=e.i(21101);function s({className:e="h-7 w-7"}){return(0,t.jsxs)("svg",{viewBox:"0 0 32 32",className:e,"aria-hidden":"true",children:[(0,t.jsx)("defs",{children:(0,t.jsxs)("linearGradient",{id:"logo-g",x1:"0",y1:"0",x2:"1",y2:"1",children:[(0,t.jsx)("stop",{offset:"0",stopColor:"#a5b4fc"}),(0,t.jsx)("stop",{offset:"0.55",stopColor:"#c4b5fd"}),(0,t.jsx)("stop",{offset:"1",stopColor:"#67e8f9"})]})}),(0,t.jsx)("rect",{x:"1",y:"1",width:"30",height:"30",rx:"9",fill:"url(#logo-g)",opacity:"0.14"}),(0,t.jsx)("rect",{x:"1.5",y:"1.5",width:"29",height:"29",rx:"8.5",fill:"none",stroke:"url(#logo-g)",strokeOpacity:"0.55"}),(0,t.jsx)("path",{d:"M16 17.5L9 10M16 17.5L23.5 11M16 17.5V25",stroke:"url(#logo-g)",strokeWidth:"1.6",strokeLinecap:"round"}),(0,t.jsx)("circle",{cx:"9",cy:"10",r:"2.2",fill:"#a5b4fc"}),(0,t.jsx)("circle",{cx:"23.5",cy:"11",r:"2.2",fill:"#67e8f9"}),(0,t.jsx)("circle",{cx:"16",cy:"25",r:"2.2",fill:"#c4b5fd"}),(0,t.jsx)("circle",{cx:"16",cy:"17.5",r:"3.3",fill:"#fbbf77"})]})}let l=[{href:"/settings",label:"Key",full:"API key",Icon:a.IconKey,step:"key"},{href:"/profile",label:"Profile",full:"Profile",Icon:a.IconUser,step:"profile"},{href:"/dashboard",label:"Match",full:"Match",Icon:a.IconCompass,step:null}];e.s(["LogoMark",0,s,"default",0,function(){let e=(0,n.usePathname)(),[c,u]=(0,o.useState)({key:!1,profile:!1});return(0,o.useEffect)(()=>{let e=()=>u({key:!!(0,i.loadSettings)()?.apiKey?.trim(),profile:!!(0,i.loadProfile)()}),t=setTimeout(e,0),r=(0,i.onSetupChanged)(e);return()=>{clearTimeout(t),r()}},[e]),(0,t.jsx)("header",{className:"sticky top-0 z-40 px-3 pt-3 sm:px-6",children:(0,t.jsxs)("div",{className:"glass mx-auto flex h-14 max-w-6xl items-center justify-between rounded-2xl pl-3 pr-2 sm:pl-4",children:[(0,t.jsxs)(r.default,{href:"/",className:"group flex items-center gap-2.5","aria-label":"PhDTake home",children:[(0,t.jsx)("span",{className:"transition-transform duration-500 group-hover:rotate-[18deg] group-hover:scale-110",children:(0,t.jsx)(s,{})}),(0,t.jsxs)("span",{className:"text-[1.05rem] font-semibold tracking-tight text-white",children:["PhD",(0,t.jsx)("span",{className:"metal-text",children:"Take"})]})]}),(0,t.jsx)("nav",{className:"flex items-center gap-1","aria-label":"Main",children:l.map(({href:n,label:o,full:i,Icon:s,step:l},u)=>{let f=e===n||e.startsWith(n+"/")||"/dashboard"===n&&e.startsWith("/runs"),d=!!l&&c[l];return(0,t.jsxs)(r.default,{href:n,"aria-current":f?"page":void 0,title:i,className:`group relative flex items-center gap-2 rounded-xl px-2.5 py-2 text-sm transition-all duration-300 sm:px-3 ${f?"bg-white/[0.08] text-white shadow-[0_0_0_1px_rgba(165,180,252,0.25)_inset]":"text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-100"}`,children:[(0,t.jsx)("span",{className:`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold transition-colors ${d?"bg-emerald-400/20 text-emerald-300":f?"bg-indigo-400/25 text-indigo-200":"bg-white/[0.06] text-zinc-500 group-hover:text-zinc-300"}`,children:d?(0,t.jsx)(a.IconCheck,{className:"h-3 w-3"}):u+1}),(0,t.jsx)(s,{className:"h-4 w-4 opacity-70 sm:hidden md:block"}),(0,t.jsx)("span",{className:"hidden sm:inline",children:o}),f&&(0,t.jsx)("span",{className:"absolute inset-x-3 -bottom-px h-px bg-gradient-to-r from-transparent via-indigo-300/80 to-transparent"})]},n)})})]})})}])},14426,e=>{"use strict";var t=e.i(43476),r=e.i(71645);let n={position:"fixed",inset:0,zIndex:-1,pointerEvents:"none",background:"radial-gradient(120% 90% at 18% 8%, rgba(79,70,229,0.20) 0%, rgba(9,9,15,0) 42%),radial-gradient(110% 100% at 85% 20%, rgba(139,92,246,0.16) 0%, rgba(9,9,15,0) 46%),radial-gradient(120% 120% at 60% 100%, rgba(34,211,238,0.12) 0%, rgba(9,9,15,0) 50%),#07070c"},o=`
  precision highp float;
  attribute vec2 position;
  varying vec2 vUv;
  void main() {
    vUv = position * 0.5 + 0.5;
    gl_Position = vec4(position, 0.0, 1.0);
  }
`,i=`
  precision highp float;
  varying vec2 vUv;
  uniform vec2  uResolution;
  uniform float uTime;
  uniform float uQuality;   // 1.0 = full, <1.0 = fewer octaves (mobile)

  // ---- hash / value noise -------------------------------------------------
  vec2 hash2(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(dot(hash2(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
          dot(hash2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
      mix(dot(hash2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
          dot(hash2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x),
      u.y);
  }

  // fractal brownian motion — flows along a fixed "data current" direction.
  float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    vec2 flow = vec2(0.14, 0.05);        // constant engineered drift
    mat2 rot = mat2(0.80, 0.60, -0.60, 0.80);
    int oct = uQuality > 0.5 ? 6 : 4;
    for (int i = 0; i < 6; i++) {
      if (i >= oct) break;
      v += a * noise(p + flow * uTime * float(i + 1) * 0.35);
      p = rot * p * 1.92 + 4.0;
      a *= 0.5;
    }
    return v;
  }

  // domain-warped height field — the "liquid" surface.
  float surface(vec2 p, out vec2 warp) {
    float t = uTime * 0.06;
    vec2 q = vec2(fbm(p + vec2(0.0, t)), fbm(p + vec2(5.2, 1.3 - t)));
    vec2 r = vec2(fbm(p + 3.0 * q + vec2(1.7, 9.2) + 0.15 * t),
                  fbm(p + 3.0 * q + vec2(8.3, 2.8) - 0.12 * t));
    warp = r;
    return fbm(p + 2.4 * r);
  }

  // metaball-like energy currents — bright cores that drift and pulse, giving the
  // "intelligence flowing through a network" read.
  float energyCurrents(vec2 uv) {
    float e = 0.0;
    for (int i = 0; i < 3; i++) {
      float fi = float(i);
      vec2 c = vec2(
        0.5 + 0.42 * sin(uTime * 0.10 + fi * 2.2),
        0.5 + 0.34 * cos(uTime * 0.08 + fi * 1.7)
      );
      float d = length((uv - c) * vec2(uResolution.x / uResolution.y, 1.0));
      e += 0.045 / (d * d + 0.02);
    }
    return e;
  }

  void main() {
    vec2 uv = vUv;
    vec2 p = (gl_FragCoord.xy - 0.5 * uResolution.xy) / uResolution.y;
    p *= 2.6;

    // height field + cheap analytic normal from finite differences.
    vec2 warp;
    float h = surface(p, warp);
    float eps = 0.012;
    vec2 w2;
    float hx = surface(p + vec2(eps, 0.0), w2);
    float hy = surface(p + vec2(0.0, eps), w2);
    vec3 n = normalize(vec3(h - hx, h - hy, eps * 3.2));

    // lighting: a single crisp "engineered" key light for the chrome highlight.
    vec3 lightDir = normalize(vec3(0.55, 0.62, 0.75));
    vec3 viewDir = vec3(0.0, 0.0, 1.0);
    vec3 halfDir = normalize(lightDir + viewDir);

    float diff = clamp(dot(n, lightDir), 0.0, 1.0);
    float spec = pow(clamp(dot(n, halfDir), 0.0, 1.0), 42.0);  // liquid-metal glint
    float fres = pow(1.0 - clamp(dot(n, viewDir), 0.0, 1.0), 3.0); // rim

    // palette — near-black base, indigo → violet body, cyan energy.
    vec3 base    = vec3(0.024, 0.024, 0.045);
    vec3 indigo  = vec3(0.31, 0.27, 0.90);
    vec3 violet  = vec3(0.55, 0.33, 0.95);
    vec3 cyan    = vec3(0.16, 0.85, 0.95);
    vec3 chrome  = vec3(0.78, 0.80, 0.92);

    float body = smoothstep(-0.35, 0.65, h);
    vec3 col = mix(base, indigo, body * 0.72);
    col = mix(col, violet, smoothstep(0.1, 0.9, warp.x * 0.5 + 0.5) * 0.45);

    // flowing "data current" veins along the warp gradient — thin bright threads.
    float veins = smoothstep(0.75, 0.99, fbm(p * 1.6 + warp * 2.0 + uTime * 0.05));
    col += cyan * veins * 0.38;

    // chrome highlight + fresnel rim = the engineered / refractive look. Kept
    // controlled so highlights don't blow out under overlaid UI text.
    col += chrome * spec * 0.85;
    col += mix(indigo, cyan, 0.5) * fres * 0.32;
    col *= 0.5 + 0.7 * diff;

    // metaball energy cores (kept subtle so the UI stays legible on top).
    float energy = energyCurrents(uv);
    col += mix(violet, cyan, 0.5) * energy * 0.26;

    // vignette so page content reads clearly toward the edges + center.
    float vig = smoothstep(1.35, 0.2, length(uv - 0.5));
    col *= 0.34 + 0.6 * vig;

    // subtle filmic-ish tonemap; hold it dark and premium (the UI does the rest).
    col = col / (col + 1.05);
    col = pow(col, vec3(0.95));

    gl_FragColor = vec4(col, 1.0);
  }
`;e.s(["default",0,function(){let a=(0,r.useRef)(null),[s,l]=(0,r.useState)(!0);return(0,r.useEffect)(()=>{let t=a.current;if(!t)return;let r=window.matchMedia?.("(prefers-reduced-motion: reduce)").matches,n=window.matchMedia?.("(max-width: 640px)").matches,s=null,c=null,u=null,f=null,d=0,h=!0,p=!0,v=null,g=!1,m=[];return(async()=>{try{let a=await e.A(21442);if(g)return;s=new a.WebGLRenderer({canvas:t,antialias:!1,alpha:!1,powerPreference:"low-power",failIfMajorPerformanceCaveat:!1});let x=Math.min(window.devicePixelRatio||1,n?1:1.5),y=n?.6:.85,w=new a.Scene,b=new a.Camera;u=new a.BufferGeometry;let j=new Float32Array([-1,-1,3,-1,-1,3]);u.setAttribute("position",new a.BufferAttribute(j,2)),u.setDrawRange(0,3),u.boundingSphere=new a.Sphere(new a.Vector3(0,0,0),2),f=new a.RawShaderMaterial({vertexShader:o,fragmentShader:i,depthTest:!1,depthWrite:!1,uniforms:{uResolution:{value:new a.Vector2(1,1)},uTime:{value:0},uQuality:{value:+!n}}}),(c=new a.Mesh(u,f)).frustumCulled=!1,w.add(c);let M=()=>{if(!s||!f)return;let e=window.innerWidth,t=window.innerHeight;s.setPixelRatio(x*y),s.setSize(e,t,!1);let r=s.getDrawingBufferSize(new a.Vector2);f.uniforms.uResolution.value.set(r.x,r.y)};M();let P=e=>{s&&f&&(f.uniforms.uTime.value=e,s.render(w,b))};if(l(!1),r){P(6),window.addEventListener("resize",()=>{M(),P(6)});return}let k=0,E=performance.now(),S=e=>{d=requestAnimationFrame(S),h&&p&&(e-k<25||(k=e,P((e-E)/1e3)))};d=requestAnimationFrame(S);let N=()=>{h=!document.hidden};document.addEventListener("visibilitychange",N),(v=new IntersectionObserver(e=>{p=e[0]?.isIntersecting??!0},{threshold:0})).observe(t),window.addEventListener("resize",M),m.push(()=>{document.removeEventListener("visibilitychange",N),window.removeEventListener("resize",M)})}catch{l(!0)}})(),()=>{g=!0,h=!1,d&&cancelAnimationFrame(d),m.forEach(e=>e()),v?.disconnect(),u?.dispose(),f?.dispose(),s&&(s.forceContextLoss?.(),s.dispose()),s=null,c=null,u=null,f=null}},[]),(0,t.jsxs)(t.Fragment,{children:[(0,t.jsx)("canvas",{ref:a,"aria-hidden":"true",className:"fluid-canvas",style:{position:"fixed",inset:0,width:"100%",height:"100%",zIndex:-1,pointerEvents:"none",display:"block"}}),s&&(0,t.jsx)("div",{"aria-hidden":"true",style:n})]})}])},70777,e=>{"use strict";var t=e.i(71645);e.s(["default",0,function(){return(0,t.useEffect)(()=>{if(window.matchMedia("(pointer: coarse)").matches)return;let e=0,t=t=>{e||(e=requestAnimationFrame(()=>{e=0;let r=t.target?.closest?.(".spotlight");if(!r)return;let n=r.getBoundingClientRect();r.style.setProperty("--mx",`${t.clientX-n.left}px`),r.style.setProperty("--my",`${t.clientY-n.top}px`)}))};return window.addEventListener("pointermove",t,{passive:!0}),()=>{window.removeEventListener("pointermove",t),cancelAnimationFrame(e)}},[]),null}])},21442,e=>{e.v(t=>Promise.all(["static/chunks/1cxyjnj-xozuv.js"].map(t=>e.l(t))).then(()=>t(32009)))}]);