const BROWSERLESS="https://production-sfo.browserless.io";

function json(message,status=400){return new Response(JSON.stringify({error:message}),{status,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}})}

export default async (req)=>{
  if(req.method!=="GET") return json("Method not allowed",405);
  const token=Netlify.env.get("BROWSERLESS_TOKEN");
  if(!token) return json("Snapshot is not configured yet. Add BROWSERLESS_TOKEN in Netlify environment variables.",503);
  const u=new URL(req.url);
  const target=u.searchParams.get("url");
  const format=u.searchParams.get("format")||"png";
  const width=Math.min(Math.max(Number(u.searchParams.get("width")||1440),320),2560);
  const delay=Math.min(Math.max(Number(u.searchParams.get("delay")||3),0),15);
  const paper=u.searchParams.get("paper")||"A4";
  try{new URL(target)}catch{return json("Invalid URL. Use a full http:// or https:// URL.")}

  const common={url:target,viewport:{width,height:900},gotoOptions:{waitUntil:"networkidle2",timeout:45000},waitForTimeout:delay*1000,scrollPage:true};
  let endpoint,body,contentType,ext;
  if(format==="pdf"){
    endpoint="/pdf";contentType="application/pdf";ext="pdf";
    body={url:target,options:{format:paper,printBackground:true,preferCSSPageSize:false,margin:{top:"0",right:"0",bottom:"0",left:"0"}}};
  }else{
    endpoint="/screenshot";const type=format==="jpeg"?"jpeg":"png";contentType=type==="jpeg"?"image/jpeg":"image/png";ext=type;
    body={...common,options:{fullPage:true,type,quality:type==="jpeg"?92:100}};
  }
  const response=await fetch(BROWSERLESS+endpoint+"?token="+encodeURIComponent(token),{method:"POST",headers:{"Content-Type":"application/json","Cache-Control":"no-cache"},body:JSON.stringify(body)});
  if(!response.ok){let detail="Browser renderer returned "+response.status;try{const t=await response.text();if(t)detail+=": "+t.slice(0,300)}catch{}return json(detail,response.status>=500?502:response.status)}
  return new Response(await response.arrayBuffer(),{status:200,headers:{"Content-Type":contentType,"Content-Disposition":"attachment; filename="+"snapshot."+ext,"Cache-Control":"no-store"}});
};

export const config={path:"/api/capture"};