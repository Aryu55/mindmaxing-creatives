(function(){
  'use strict';
  // A small procedural study, deliberately separate from the client garment model.
  globalThis.GarmentRenderer=function(canvas){
    const gl=canvas.getContext('webgl',{alpha:true,antialias:true,preserveDrawingBuffer:true});if(!gl)return null;
    // Fit the shoulders as well as the height on narrow/tablet canvases.
    const vertex=`attribute vec3 position;attribute vec3 normal;uniform float angle;uniform float aspect;varying vec3 n;varying vec3 p;void main(){float c=cos(angle),s=sin(angle);mat3 rotation=mat3(c,0.,-s,0.,1.,0.,s,0.,c);vec3 v=rotation*position;v.y+=.03;p=position;n=rotation*normal;float depth=3.6-v.z;float scale=min(4.05,3.15*aspect);gl_Position=vec4(v.x*scale/aspect,v.y*scale,v.z*.04,depth);}`;
    const fragment=`precision mediump float;varying vec3 n;varying vec3 p;uniform vec3 colour;uniform float sheen;void main(){vec3 N=normalize(n);vec3 light=normalize(vec3(-.65,.9,1.3));float diffuse=max(dot(N,light),0.);float rim=pow(1.-abs(N.z),2.)*.2;float spec=pow(max(dot(N,normalize(light+vec3(0.,0.,1.))),0.),mix(8.,70.,sheen));float weave=sin(p.x*320.)*sin(p.y*380.)*.018;float folds=sin(p.y*13.+p.x*9.)*.025;vec3 result=colour*(.33+diffuse*.65+rim+weave+folds)+vec3(1.,.94,.84)*spec*sheen*.4;gl_FragColor=vec4(result,1.);}`;
    function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error('Shader compilation failed');return s;}
    const vs=shader(gl.VERTEX_SHADER,vertex),fs=shader(gl.FRAGMENT_SHADER,fragment),program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('Shader link failed');gl.useProgram(program);
    let vertices=[];
    function tube(rings,segments=64,axis=[0,1,0]){
      const u=[axis[1],-axis[0],0],v=[0,0,1],len=Math.hypot(...u);u[0]/=len;u[1]/=len;
      const sample=(r,t)=>{const c=Math.cos(t),s=Math.sin(t);return [r[0]+u[0]*c*r[3],r[1]+u[1]*c*r[3],r[2]+s*r[4],u[0]*c,u[1]*c,s];};
      for(let j=0;j<rings.length-1;j++)for(let i=0;i<segments;i++){const a=i/segments*Math.PI*2,b=(i+1)/segments*Math.PI*2,A=sample(rings[j],a),B=sample(rings[j],b),C=sample(rings[j+1],a),D=sample(rings[j+1],b);vertices.push(...A,...C,...B,...B,...C,...D);}
    }
    // Contoured body with an open neck and softly rounded hem.
    tube([[0,-.73,0,.405,.14],[0,-.69,0,.425,.155],[0,-.35,0,.39,.15],[0,0,0,.41,.175],[0,.32,0,.47,.18],[0,.47,0,.44,.16],[0,.57,0,.21,.13],[0,.59,0,.17,.115]],80);
    // Short sleeves, angled away from the shoulder.
    for(const side of [-1,1])tube([[side*.38,.36,0,.195,.17],[side*.53,.23,0,.19,.165],[side*.75,.05,0,.175,.15],[side*.78,.03,0,.17,.145]],48,[side*.74,-.67,0]);
    tube([[0,.575,0,.177,.12],[0,.603,0,.175,.118],[0,.613,0,.165,.11]],64);
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);for(const [name,offset]of [['position',0],['normal',12]]){const a=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,3,gl.FLOAT,false,24,offset);}gl.enable(gl.DEPTH_TEST);
    const loc={angle:gl.getUniformLocation(program,'angle'),aspect:gl.getUniformLocation(program,'aspect'),colour:gl.getUniformLocation(program,'colour'),sheen:gl.getUniformLocation(program,'sheen')};let state=[-20,0],active=true;
    function draw(angle=state[0],material=state[1]){state=[angle,material];if(!active||document.hidden)return;const rect=canvas.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,2);canvas.width=Math.max(1,Math.round(rect.width*ratio));canvas.height=Math.max(1,Math.round(rect.height*ratio));gl.viewport(0,0,canvas.width,canvas.height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.uniform1f(loc.angle,angle*Math.PI/180);gl.uniform1f(loc.aspect,canvas.width/canvas.height);gl.uniform3fv(loc.colour,[[.57,.66,.60],[.72,.59,.44],[.47,.57,.73]][material]);gl.uniform1f(loc.sheen,[.15,.05,.85][material]);gl.drawArrays(gl.TRIANGLES,0,vertices.length/6);}
    const resize=new ResizeObserver(()=>draw());resize.observe(canvas);
    return{draw,setActive(value){const resume=!active&&value;active=Boolean(value);if(resume)draw();},destroy(){resize.disconnect();gl.deleteBuffer(buffer);gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);gl.getExtension('WEBGL_lose_context')?.loseContext();}};
  };
})();
