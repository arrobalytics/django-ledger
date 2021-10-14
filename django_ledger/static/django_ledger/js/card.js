const hyperlinkCards = document.getElementsByClassName("hyperlink-card");

for (card of hyperlinkCards){
    card.addEventListener('click',
        (e)=>{
        const el = e.currentTarget;
        window.location = el.firstElementChild.href;
    }, false);
}