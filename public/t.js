// Tires for Anything click counter. Counts which buttons get used, by page. No cookies, no personal data.
(function(){
  function page(){var p=location.pathname.replace(/^\/|\/$/g,"");return p||"home";}
  function send(ev){
    try{
      var body=JSON.stringify({e:ev,p:page()});
      if(navigator.sendBeacon){navigator.sendBeacon("/api/event",new Blob([body],{type:"application/json"}));}
      else{fetch("/api/event",{method:"POST",headers:{"Content-Type":"application/json"},body:body,keepalive:true});}
    }catch(e){}
  }
  window.tfaTrack=send;
  document.addEventListener("click",function(e){
    var a=e.target.closest&&e.target.closest("a,button");if(!a)return;
    var href=a.getAttribute("href")||"";
    if(/amazon\.com/.test(href))send("amazon");
    else if(/darksidetires\.com/.test(href))send("darkside");
    else if(/google\.com\/maps/.test(href))send("find_shop");
    else if(href==="#quote"||/\/tire-quotes\/$/.test(href))send("quote_open");
    else if(href==="#request"||/\/find-my-tire\/$/.test(href))send("request_open");
    else if(a.id==="dec-go"||a.id==="home-go")send("decode");
  },true);
})();
