(globalThis.TURBOPACK||(globalThis.TURBOPACK=[])).push(["object"==typeof document?document.currentScript:void 0,98183,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0});var n={assign:function(){return s},searchParamsToUrlQuery:function(){return i},urlQueryToSearchParams:function(){return l}};for(var o in n)Object.defineProperty(r,o,{enumerable:!0,get:n[o]});function i(e){let t={};for(let[r,n]of e.entries()){let e=t[r];void 0===e?t[r]=n:Array.isArray(e)?e.push(n):t[r]=[e,n]}return t}function a(e){return"string"==typeof e?e:("number"!=typeof e||isNaN(e))&&"boolean"!=typeof e?"":String(e)}function l(e){let t=new URLSearchParams;for(let[r,n]of Object.entries(e))if(Array.isArray(n))for(let e of n)t.append(r,a(e));else t.set(r,a(n));return t}function s(e,...t){for(let r of t){for(let t of r.keys())e.delete(t);for(let[t,n]of r.entries())e.append(t,n)}return e}},18967,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0});var n={DecodeError:function(){return g},MiddlewareNotFoundError:function(){return x},MissingStaticPage:function(){return w},NormalizeError:function(){return y},PageNotFoundError:function(){return b},SP:function(){return v},ST:function(){return m},WEB_VITALS:function(){return i},execOnce:function(){return a},getDisplayName:function(){return f},getLocationOrigin:function(){return u},getURL:function(){return c},isAbsoluteUrl:function(){return s},isResSent:function(){return d},loadGetInitialProps:function(){return h},normalizeRepeatedSlashes:function(){return p},stringifyError:function(){return P}};for(var o in n)Object.defineProperty(r,o,{enumerable:!0,get:n[o]});let i=["CLS","FCP","FID","INP","LCP","TTFB"];function a(e){let t,r=!1;return(...n)=>(r||(r=!0,t=e(...n)),t)}let l=/^[a-zA-Z][a-zA-Z\d+\-.]*?:/,s=e=>l.test(e);function u(){let{protocol:e,hostname:t,port:r}=window.location;return`${e}//${t}${r?":"+r:""}`}function c(){let{href:e}=window.location,t=u();return e.substring(t.length)}function f(e){return"string"==typeof e?e:e.displayName||e.name||"Unknown"}function d(e){return e.finished||e.headersSent}function p(e){let t=e.split("?");return t[0].replace(/\\/g,"/").replace(/\/\/+/g,"/")+(t[1]?`?${t.slice(1).join("?")}`:"")}async function h(e,t){let r=t.res||t.ctx&&t.ctx.res;if(!e.getInitialProps)return t.ctx&&t.Component?{pageProps:await h(t.Component,t.ctx)}:{};let n=await e.getInitialProps(t);if(r&&d(r))return n;if(!n)throw Object.defineProperty(Error(`"${f(e)}.getInitialProps()" should resolve to an object. But found "${n}" instead.`),"__NEXT_ERROR_CODE",{value:"E1025",enumerable:!1,configurable:!0});return n}let v="u">typeof performance,m=v&&["mark","measure","getEntriesByName"].every(e=>"function"==typeof performance[e]);class g extends Error{}class y extends Error{}class b extends Error{constructor(e){super(),this.code="ENOENT",this.name="PageNotFoundError",this.message=`Cannot find module for page: ${e}`}}class w extends Error{constructor(e,t){super(),this.message=`Failed to load static file for page: ${e} ${t}`}}class x extends Error{constructor(){super(),this.code="ENOENT",this.message="Cannot find the middleware module"}}function P(e){return JSON.stringify({message:e.message,stack:e.stack})}},33525,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"warnOnce",{enumerable:!0,get:function(){return n}});let n=e=>{}},95057,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0});var n={formatUrl:function(){return l},formatWithValidation:function(){return u},urlObjectKeys:function(){return s}};for(var o in n)Object.defineProperty(r,o,{enumerable:!0,get:n[o]});let i=e.r(90809)._(e.r(98183)),a=/https?|ftp|gopher|file/;function l(e){let{auth:t,hostname:r}=e,n=e.protocol||"",o=e.pathname||"",l=e.hash||"",s=e.query||"",u=!1;t=t?encodeURIComponent(t).replace(/%3A/i,":")+"@":"",e.host?u=t+e.host:r&&(u=t+(~r.indexOf(":")?`[${r}]`:r),e.port&&(u+=":"+e.port)),s&&"object"==typeof s&&(s=String(i.urlQueryToSearchParams(s)));let c=e.search||s&&`?${s}`||"";return n&&!n.endsWith(":")&&(n+=":"),e.slashes||(!n||a.test(n))&&!1!==u?(u="//"+(u||""),o&&"/"!==o[0]&&(o="/"+o)):u||(u=""),l&&"#"!==l[0]&&(l="#"+l),c&&"?"!==c[0]&&(c="?"+c),o=o.replace(/[?#]/g,encodeURIComponent),c=c.replace("#","%23"),`${n}${u}${o}${c}${l}`}let s=["auth","hash","host","hostname","href","path","pathname","port","protocol","query","search","slashes"];function u(e){return l(e)}},18581,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"useMergedRef",{enumerable:!0,get:function(){return o}});let n=e.r(71645);function o(e,t){let r=(0,n.useRef)(null),o=(0,n.useRef)(null);return(0,n.useCallback)(n=>{if(null===n){let e=r.current;e&&(r.current=null,e());let t=o.current;t&&(o.current=null,t())}else e&&(r.current=i(e,n)),t&&(o.current=i(t,n))},[e,t])}function i(e,t){if("function"!=typeof e)return e.current=t,()=>{e.current=null};{let r=e(t);return"function"==typeof r?r:()=>e(null)}}("function"==typeof r.default||"object"==typeof r.default&&null!==r.default)&&void 0===r.default.__esModule&&(Object.defineProperty(r.default,"__esModule",{value:!0}),Object.assign(r.default,r),t.exports=r.default)},73668,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"isLocalURL",{enumerable:!0,get:function(){return i}});let n=e.r(18967),o=e.r(52817);function i(e){if(!(0,n.isAbsoluteUrl)(e))return!0;try{let t=(0,n.getLocationOrigin)(),r=new URL(e,t);return r.origin===t&&(0,o.hasBasePath)(r.pathname)}catch(e){return!1}}},84508,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0}),Object.defineProperty(r,"errorOnce",{enumerable:!0,get:function(){return n}});let n=e=>{}},22016,(e,t,r)=>{"use strict";Object.defineProperty(r,"__esModule",{value:!0});var n={default:function(){return g},useLinkStatus:function(){return b}};for(var o in n)Object.defineProperty(r,o,{enumerable:!0,get:n[o]});let i=e.r(90809),a=e.r(43476),l=i._(e.r(71645)),s=e.r(95057),u=e.r(8372),c=e.r(18581),f=e.r(18967),d=e.r(5550);e.r(33525);let p=e.r(88540),h=e.r(91949),v=e.r(73668),m=e.r(9396);function g(t){var r,n;let o,i,g,[b,w]=(0,l.useOptimistic)(h.IDLE_LINK_STATUS),x=(0,l.useRef)(null),{href:P,as:j,children:_,prefetch:E=null,passHref:S,replace:O,shallow:T,scroll:R,onClick:C,onMouseEnter:N,onTouchStart:k,legacyBehavior:L=!1,onNavigate:A,transitionTypes:M,ref:U,unstable_dynamicOnHover:I,...D}=t;o=_,L&&("string"==typeof o||"number"==typeof o)&&(o=(0,a.jsx)("a",{children:o}));let z=l.default.useContext(u.AppRouterContext),F=!1!==E,$=!1!==E?null===(n=E)||"auto"===n?m.FetchStrategy.PPR:m.FetchStrategy.Full:m.FetchStrategy.PPR,B="string"==typeof(r=j||P)?r:(0,s.formatUrl)(r);if(L){if(o?.$$typeof===Symbol.for("react.lazy"))throw Object.defineProperty(Error("`<Link legacyBehavior>` received a direct child that is either a Server Component, or JSX that was loaded with React.lazy(). This is not supported. Either remove legacyBehavior, or make the direct child a Client Component that renders the Link's `<a>` tag."),"__NEXT_ERROR_CODE",{value:"E863",enumerable:!1,configurable:!0});i=l.default.Children.only(o)}let K=L?i&&"object"==typeof i&&i.ref:U,q=l.default.useCallback(e=>(null!==z&&(x.current=(0,h.mountLinkInstance)(e,B,z,$,F,w)),()=>{x.current&&((0,h.unmountLinkForCurrentNavigation)(x.current),x.current=null),(0,h.unmountPrefetchableInstance)(e)}),[F,B,z,$,w]),W={ref:(0,c.useMergedRef)(q,K),onClick(t){L||"function"!=typeof C||C(t),L&&i.props&&"function"==typeof i.props.onClick&&i.props.onClick(t),!z||t.defaultPrevented||function(t,r,n,o,i,a,s){if("u">typeof window){let u,{nodeName:c}=t.currentTarget;if("A"===c.toUpperCase()&&((u=t.currentTarget.getAttribute("target"))&&"_self"!==u||t.metaKey||t.ctrlKey||t.shiftKey||t.altKey||t.nativeEvent&&2===t.nativeEvent.which)||t.currentTarget.hasAttribute("download"))return;if(!(0,v.isLocalURL)(r)){o&&(t.preventDefault(),location.replace(r));return}if(t.preventDefault(),a){let e=!1;if(a({preventDefault:()=>{e=!0}}),e)return}let{dispatchNavigateAction:f}=e.r(99781);l.default.startTransition(()=>{f(r,o?"replace":"push",!1===i?p.ScrollBehavior.NoScroll:p.ScrollBehavior.Default,n.current,s)})}}(t,B,x,O,R,A,M)},onMouseEnter(e){L||"function"!=typeof N||N(e),L&&i.props&&"function"==typeof i.props.onMouseEnter&&i.props.onMouseEnter(e),z&&F&&(0,h.onNavigationIntent)(e.currentTarget,!0===I)},onTouchStart:function(e){L||"function"!=typeof k||k(e),L&&i.props&&"function"==typeof i.props.onTouchStart&&i.props.onTouchStart(e),z&&F&&(0,h.onNavigationIntent)(e.currentTarget,!0===I)}};return(0,f.isAbsoluteUrl)(B)?W.href=B:L&&!S&&("a"!==i.type||"href"in i.props)||(W.href=(0,d.addBasePath)(B)),g=L?l.default.cloneElement(i,W):(0,a.jsx)("a",{...D,...W,children:o}),(0,a.jsx)(y.Provider,{value:b,children:g})}e.r(84508);let y=(0,l.createContext)(h.IDLE_LINK_STATUS),b=()=>(0,l.useContext)(y);("function"==typeof r.default||"object"==typeof r.default&&null!==r.default)&&void 0===r.default.__esModule&&(Object.defineProperty(r.default,"__esModule",{value:!0}),Object.assign(r.default,r),t.exports=r.default)},18566,(e,t,r)=>{t.exports=e.r(76562)},42724,e=>{"use strict";var t=e.i(43476),r=e.i(22016),n=e.i(18566);e.s(["default",0,function(){let e=(0,n.usePathname)(),o=t=>`rounded-md px-3 py-1.5 text-sm transition-colors ${e===t||e.startsWith(t+"/")?"bg-indigo-500/15 text-indigo-200":"text-zinc-400 hover:text-zinc-100 hover:bg-white/5"}`;return(0,t.jsx)("header",{className:"sticky top-0 z-40 border-b border-white/10 bg-[#07070c]/55 backdrop-blur-xl backdrop-saturate-150 supports-[backdrop-filter]:bg-[#07070c]/45",children:(0,t.jsxs)("div",{className:"mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6",children:[(0,t.jsxs)(r.default,{href:"/",className:"group flex items-center gap-2",children:[(0,t.jsx)("span",{className:"metal-fill relative inline-block h-6 w-6 rounded-md shadow-[0_0_18px_rgba(99,102,241,0.55)] transition-transform duration-300 group-hover:scale-110",children:(0,t.jsx)("span",{className:"absolute inset-0 rounded-md bg-white/20 opacity-0 transition-opacity duration-300 group-hover:opacity-100"})}),(0,t.jsxs)("span",{className:"text-lg font-semibold tracking-tight text-white",children:["PhD",(0,t.jsx)("span",{className:"metal-text",children:"Take"})]})]}),(0,t.jsxs)("nav",{className:"flex items-center gap-1",children:[(0,t.jsx)(r.default,{href:"/dashboard",className:o("/dashboard"),children:"Dashboard"}),(0,t.jsx)(r.default,{href:"/profile",className:o("/profile"),children:"Profile"}),(0,t.jsx)(r.default,{href:"/settings",className:o("/settings"),children:"Settings"})]})]})})}])},14426,e=>{"use strict";var t=e.i(43476),r=e.i(71645);let n={position:"fixed",inset:0,zIndex:-1,pointerEvents:"none",background:"radial-gradient(120% 90% at 18% 8%, rgba(79,70,229,0.20) 0%, rgba(9,9,15,0) 42%),radial-gradient(110% 100% at 85% 20%, rgba(139,92,246,0.16) 0%, rgba(9,9,15,0) 46%),radial-gradient(120% 120% at 60% 100%, rgba(34,211,238,0.12) 0%, rgba(9,9,15,0) 50%),#07070c"},o=`
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
`;e.s(["default",0,function(){let a=(0,r.useRef)(null),[l,s]=(0,r.useState)(!0);return(0,r.useEffect)(()=>{let t=a.current;if(!t)return;let r=window.matchMedia?.("(prefers-reduced-motion: reduce)").matches,n=window.matchMedia?.("(max-width: 640px)").matches,l=null,u=null,c=null,f=null,d=0,p=!0,h=!0,v=null,m=!1,g=[];return(async()=>{try{let a=await e.A(21442);if(m)return;l=new a.WebGLRenderer({canvas:t,antialias:!1,alpha:!1,powerPreference:"low-power",failIfMajorPerformanceCaveat:!1});let y=Math.min(window.devicePixelRatio||1,n?1:1.5),b=n?.6:.85,w=new a.Scene,x=new a.Camera;c=new a.BufferGeometry;let P=new Float32Array([-1,-1,3,-1,-1,3]);c.setAttribute("position",new a.BufferAttribute(P,2)),c.setDrawRange(0,3),c.boundingSphere=new a.Sphere(new a.Vector3(0,0,0),2),f=new a.RawShaderMaterial({vertexShader:o,fragmentShader:i,depthTest:!1,depthWrite:!1,uniforms:{uResolution:{value:new a.Vector2(1,1)},uTime:{value:0},uQuality:{value:+!n}}}),(u=new a.Mesh(c,f)).frustumCulled=!1,w.add(u);let j=()=>{if(!l||!f)return;let e=window.innerWidth,t=window.innerHeight;l.setPixelRatio(y*b),l.setSize(e,t,!1);let r=l.getDrawingBufferSize(new a.Vector2);f.uniforms.uResolution.value.set(r.x,r.y)};j();let _=e=>{l&&f&&(f.uniforms.uTime.value=e,l.render(w,x))};if(s(!1),r){_(6),window.addEventListener("resize",()=>{j(),_(6)});return}let E=0,S=performance.now(),O=e=>{d=requestAnimationFrame(O),p&&h&&(e-E<25||(E=e,_((e-S)/1e3)))};d=requestAnimationFrame(O);let T=()=>{p=!document.hidden};document.addEventListener("visibilitychange",T),(v=new IntersectionObserver(e=>{h=e[0]?.isIntersecting??!0},{threshold:0})).observe(t),window.addEventListener("resize",j),g.push(()=>{document.removeEventListener("visibilitychange",T),window.removeEventListener("resize",j)})}catch{s(!0)}})(),()=>{m=!0,p=!1,d&&cancelAnimationFrame(d),g.forEach(e=>e()),v?.disconnect(),c?.dispose(),f?.dispose(),l&&(l.forceContextLoss?.(),l.dispose()),l=null,u=null,c=null,f=null}},[]),(0,t.jsxs)(t.Fragment,{children:[(0,t.jsx)("canvas",{ref:a,"aria-hidden":"true",className:"fluid-canvas",style:{position:"fixed",inset:0,width:"100%",height:"100%",zIndex:-1,pointerEvents:"none",display:"block"}}),l&&(0,t.jsx)("div",{"aria-hidden":"true",style:n})]})}])},21442,e=>{e.v(t=>Promise.all(["static/chunks/1cxyjnj-xozuv.js"].map(t=>e.l(t))).then(()=>t(32009)))}]);