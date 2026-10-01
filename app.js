const tg = window.Telegram.WebApp;
tg.expand(); // Mini Appni to'liq ekranga yozish

let state = {
    hp: 100,
    armor: 75,
    kills: 0,
    alive: 98,
    weapon: "M416 (30/90)",
    inventory: "Medkit x2, Granata x1"
};

const choices = [
    ["🏠 Bino ichiga kirib loot qilish", "🚗 Atrofda mashina izlash", "🎯 Tomga chiqib atroflarni kuzatish"],
    ["🎯 Qarshi o'q uzish", "💣 Granata otish", "🩹 Qochib medkit ishlatish"],
    ["🚗 Mashinada zonaga qochish", "🏕 Poya qilish", "📦 Airdrop-ga yugurish"]
];

function updateUI(storyText, newChoices) {
    document.getElementById('hp-bar').style.width = `${state.hp}%`;
    document.getElementById('hp-val').innerText = `${state.hp}/100`;
    document.getElementById('armor-bar').style.width = `${state.armor}%`;
    document.getElementById('armor-val').innerText = `${state.armor}/100`;
    document.getElementById('alive-count').innerText = state.alive;
    document.getElementById('kills-count').innerText = state.kills;
    document.getElementById('weapon-val').innerText = state.weapon;
    document.getElementById('story-text').innerText = storyText;

    const box = document.getElementById('choices-box');
    box.innerHTML = '';
    newChoices.forEach((ch, idx) => {
        const btn = document.createElement('button');
        btn.className = 'action-btn';
        btn.innerText = ch;
        btn.onclick = () => makeAction(idx);
        box.appendChild(btn);
    });
}

function makeAction(idx) {
    tg.HapticFeedback.impactOccurred('medium'); // Telefon vibratsiyasi

    state.hp = Math.max(0, state.hp - Math.floor(Math.random() * 20));
    state.armor = Math.max(0, state.armor - Math.floor(Math.random() * 15));
    if (Math.random() > 0.5) state.kills += 1;
    state.alive = Math.max(1, state.alive - Math.floor(Math.random() * 5));

    if (state.hp <= 0) {
        updateUI("☠️ Siz halok bo'ldingiz! Jang tugadi.", ["🔄 Yangi O'yin"]);
        return;
    }

    const randomChoiceSet = choices[Math.floor(Math.random() * choices.length)];
    const stories = [
        "Dushman tomonda harakat sezildi! O'qlar devorga tegib uchqun sochmoqda.",
        "Siz muvaffaqiyatli ravishda pozitsiyani egalladingiz va yangi qurol topdingiz!",
        "Zona toraymoqda! Taktik harakatni tezroq tanlang."
    ];
    
    updateUI(stories[Math.floor(Math.random() * stories.length)], randomChoiceSet);
}
