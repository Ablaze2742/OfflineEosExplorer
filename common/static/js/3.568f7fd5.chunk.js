(this["webpackJsonpeos-host"]=this["webpackJsonpeos-host"]||[]).push([[3],{186:function(e,n,t){},187:function(e,n,t){e.exports={root:"Button_root__hjJzV"}},188:function(e,n,t){e.exports={root:"ButtonContainer_root__2vvJA"}},189:function(e,n,t){e.exports={root:"HorizWrapper_root__1cT3L"}},190:function(e,n,t){e.exports={root:"Image_root__3T63R"}},191:function(e,n,t){e.exports={root:"MultWrapper_root__3w299"}},192:function(e,n,t){e.exports={root:"Text_root__2g0Me"}},193:function(e,n,t){e.exports={root:"Page_root__3alPK",main:"Page_main__3tpbp",sideBar:"Page_sideBar__fVmxa",instruction:"Page_instruction__vXvLE",action:"Page_action__21uq-",text:"Page_text__1sHZE",media:"Page_media__1TjlW"}},194:function(e,n,t){e.exports={root:"VertWrapper_root__3KDFK"}},199:function(e,n,t){"use strict";t.r(n);t(186);var r=t(0),a=t.n(r),o=t(38),c=t(4),u=t(8),s=t.n(u),i=t(187),m=t.n(i),l=function(e){var n=e.children,t=e.className,r=Object(c.a)(e,["children","className"]);return a.a.createElement("button",Object.assign({className:s()(m.a.root,t)},r),n)},d=t(188),p=t.n(d),f=function(e){var n=e.children,t=e.className,r=Object(c.a)(e,["children","className"]);return a.a.createElement("div",Object.assign({className:s()(p.a.root,t)},r),n)},v=t(46),_=t.n(v),h=function(e){e.deps;var n=e.host,t=e.opts,r=e.getCommand,c=t.map((function(e){return{label:e.label,commands:e.commands.map((function(e){return r(e)}))}}));return{run:function(){},render:function(e){return a.a.createElement("div",null,c.map((function(e,t){var r=e.label,c=e.commands,u=Object(o.a)(r);return a.a.createElement(f,{key:t},a.a.createElement(l,{onClick:function(){n.runCommands(c)}},_()(u)))})))}}},E=function(e){e.deps,e.host,e.opts;return{}},g=t(189),C=t.n(g),N=function(e){var n=e.children,t=e.className,r=Object(c.a)(e,["children","className"]);return a.a.createElement("div",Object.assign({className:s()(C.a.root,t)},r),n)},b=function(e){e.deps,e.host;var n=e.opts,t=e.getCommand,r=n.elements.map((function(e){return t(e)}));return{run:function(){return Promise.all(r.map((function(e){return e.run()})))},render:function(e){return a.a.createElement(N,null,r.filter((function(e){return!!e.render})).map((function(e,n){return a.a.createElement("div",{key:n},e.render())})))}}},j=t(1),x=t.n(j),O=t(5),y=t(75),P=t(190),k=t.n(P),T=function(e){e.children;var n=e.className,t=e.src,r=e.style,o=Object(c.a)(e,["children","className","src","style"]);return a.a.createElement("img",Object.assign({src:t,alt:"",className:s()(k.a.root,n),crossOrigin:"anonymous",style:{style:r}},o))},w=function(e){var n=e.deps,t=(e.host,e.opts),r=n(y.a),o=r.resolveLocator({type:"image/jpeg",locator:t,size:"xl"});return{render:function(e){return a.a.createElement(T,{src:o.href})},load:function(){var e=Object(O.a)(x.a.mark((function e(){return x.a.wrap((function(e){for(;;)switch(e.prev=e.next){case 0:return e.next=2,r.preload(o);case 2:case"end":return e.stop()}}),e)})));return function(){return e.apply(this,arguments)}}(),unload:function(){r.revoke(o)}}},B=t(191),M=t.n(B),z=function(e){var n=e.children,t=e.className,r=Object(c.a)(e,["children","className"]);return a.a.createElement("div",Object.assign({className:s()(M.a.root,t)},r),n)},A=function(e){e.deps,e.host;var n=e.opts,t=e.getCommand,o=n.map((function(e){return t(e)}));return{run:function(){return Promise.all(o.map((function(e){return e.run()})))},render:function(e){return a.a.createElement(z,null,o.filter((function(e){return!!e.render})).map((function(e,n){return a.a.createElement(r.Fragment,{key:n},e.render())})))}}},I=t(192),J=t.n(I),W=function(e){var n=e.children,t=e.className,r=Object(c.a)(e,["children","className"]);return a.a.createElement("div",Object.assign({className:s()(J.a.root,t)},r),n)},F=function(e){e.deps,e.host;var n=e.opts,t=Object(o.a)(n);return{render:function(e){return a.a.createElement(W,null,_()(t))}}},K=t(101),L=t(20),V=t(50),H=function(e){e.host;var n=e.deps,t=e.opts,r=e.getCommand,o=n(L.a),c=Object(V.a)(t.duration),u=(t.commands||[]).map((function(e){return r(e)}));return{run:function(){},unload:function(){void 0},render:function(){return a.a.createElement(K.a,{duration:c.milliseconds(),style:t.style,onComplete:function(){u.length&&o.setQueue(u)}})}}},q=t(193),D=t.n(q),Q=function(e){var n=e.MediaComponent,t=e.TextComponent,r=e.ActionComponent,o=e.InstructionComponent,u=e.className,i=Object(c.a)(e,["MediaComponent","TextComponent","ActionComponent","InstructionComponent","className"]);return a.a.createElement("div",Object.assign({className:s()(D.a.root,u)},i),a.a.createElement("div",{className:D.a.main},a.a.createElement("div",{className:D.a.media},n?a.a.createElement(n,null):null),a.a.createElement("div",{className:D.a.text},t&&a.a.createElement(t,null))),r||o?a.a.createElement("div",{className:D.a.sideBar},a.a.createElement("div",{className:D.a.instruction},o&&a.a.createElement(o,null)),a.a.createElement("div",{className:D.a.action},r&&a.a.createElement(r,null))):null)},R=function(e){e.deps,e.host;var n=e.opts,t=e.getCommand,r=n.text,o=n.action,c=n.media,u=n.hidden,s=n.instruc,i=r&&t({"nyx.text":r}),m=r&&i.render,l=o&&t(o),d=o&&l.render,p=c&&t(c),f=c&&p.render,v=u&&t(u),_=s&&t(s),h=s&&_.render;return{run:function(){return Promise.all([l&&l.run&&l.run(),p&&p.run&&p.run(),v&&v.run&&v.run(),_&&_.run&&_.run()])},render:function(){return a.a.createElement(Q,{TextComponent:m,MediaComponent:f,ActionComponent:d,InstructionComponent:h})}}},X=t(194),Z=t.n(X),G=function(e){var n=e.children,t=e.className,r=Object(c.a)(e,["children","className"]);return a.a.createElement("div",Object.assign({className:s()(Z.a.root,t)},r),n)},S=function(e){e.deps,e.host;var n=e.opts,t=e.getCommand,o=n.elements.map((function(e){return t(e)}));return{run:function(){return Promise.all(o.map((function(e){return e.run()})))},render:function(e){return a.a.createElement(G,null,o.filter((function(e){return!!e.render})).map((function(e,n){return a.a.createElement(r.Fragment,{key:n},e.render())})))}}};n.default=function(){return{commands:{buttonsCommand:h,dummyCommand:E,horizCommand:b,imageCommand:w,multCommand:A,textCommand:F,timerCommand:H,pageCommand:R,vertCommand:S}}}}}]);
//# sourceMappingURL=3.568f7fd5.chunk.js.map