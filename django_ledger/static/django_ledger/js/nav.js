let card = document.createElement('null');
let toggle = null;

const overlay = document.createElement('div');

const showCard = (cardId, toggleId) => {
    card.style.display = 'none';
    card = document.getElementById(cardId);
    card.style.display = 'block';
    toggle = document.getElementById(toggleId);
    document.body.appendChild(overlay);
    overlay.style.height = `${document.documentElement.scrollHeight}px`;
    overlay.style.width = '100%';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    overlay.style.position = 'absolute';
    overlay.style.display = 'block';
    overlay.id = 'overlay';
    overlay.style.top = 0;
}

document.addEventListener(
        'click',
        (e) => {
            const bounds = e.composedPath();
            if( ! (bounds.includes(toggle) || bounds.includes(card))){
            console.log(bounds);
            card.style.display = 'none';
            document.body.removeChild(overlay);

            }
        },
        false);



