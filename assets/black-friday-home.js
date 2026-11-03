/* Hide the seasonal hero after the Black Friday offer ends in Minsk time. */
(function () {
  const parts = {};
  new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Minsk",year:"numeric",month:"2-digit",day:"2-digit"})
    .formatToParts(new Date()).forEach(p=>{parts[p.type]=p.value});
  const today = parts.year+"-"+parts.month+"-"+parts.day;
  if (today > "2026-11-29") {
    document.documentElement.classList.add("ev-bf-campaign-ended");
    document.addEventListener("DOMContentLoaded",function(){
      document.querySelector("#rec1028545506 .ev-bf-home")?.remove();
    },{once:true});
  }
})();
