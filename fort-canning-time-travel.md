# Fort Canning Time Portal: Website Code

A single-file website where tourists drag a time dial through five eras of Fort Canning Hill, Singapore. The whole page changes colour and story with each era, and visitors can stamp a "passport" for the spots they have visited.

## How to use

1. Copy the code block below into a new file named `index.html`.
2. Double-click the file to open it in a browser. No build step or server is needed.
3. To put it online, upload the file to any static host (GitHub Pages, Netlify, Vercel).

## Full code (`index.html`)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fort Canning Time Portal</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,800&family=Instrument+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #14281f; --ink: #f1e7c8; --accent: #e0b84a; --panel: rgba(255,255,255,.07);
    --display: "Fraunces", Georgia, serif;
    --body: "Instrument Sans", system-ui, sans-serif;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; }
  body {
    background: var(--bg); color: var(--ink); font-family: var(--body);
    line-height: 1.6; min-height: 100vh;
    transition: background .8s ease, color .8s ease;
  }
  main { max-width: 760px; margin: 0 auto; padding: 24px 20px 64px; }
  header p { margin: 0; font-weight: 600; }

  /* Hero: the dial and the year */
  .hero { text-align: center; padding: 28px 0 8px; }
  .dial { width: min(70vw, 280px); height: auto; display: block; margin: 0 auto; }
  .dial .ring { transform-origin: 100px 100px; transition: transform 1s cubic-bezier(.3,.8,.2,1); }
  .dial circle, .dial line { stroke: var(--ink); fill: none; transition: stroke .8s; }
  .dial .hand { stroke: var(--accent); stroke-width: 4; stroke-linecap: round; }
  .dial .dot { fill: var(--accent); stroke: none; }
  .year {
    font-family: var(--display); font-weight: 800; font-size: clamp(3rem, 14vw, 5.5rem);
    line-height: 1; margin: 16px 0 4px; color: var(--accent); transition: color .8s;
  }
  .era-name { font-family: var(--display); font-weight: 500; font-size: 1.4rem; margin: 0; }

  /* Slider */
  .slider-wrap { margin: 28px 0 8px; }
  input[type=range] { width: 100%; accent-color: var(--accent); height: 32px; }
  .stops { display: flex; justify-content: space-between; gap: 4px; }
  .stops button {
    flex: 1; background: none; border: 0; color: var(--ink); opacity: .6;
    font: 600 .8rem var(--body); padding: 10px 2px; cursor: pointer; min-height: 44px;
    border-top: 3px solid transparent;
  }
  .stops button[aria-current="true"] { opacity: 1; border-top-color: var(--accent); }

  /* Story */
  article { margin-top: 24px; max-width: 62ch; margin-inline: auto; }
  article h2 { font-family: var(--display); font-size: 1.7rem; margin: 0 0 8px; }
  article p { margin: 0 0 14px; font-size: 1.05rem; }
  .spot {
    background: var(--panel); border-left: 4px solid var(--accent);
    padding: 14px 16px; border-radius: 0 10px 10px 0; margin-top: 20px;
  }
  .spot h3 { margin: 0 0 4px; font-size: 1rem; }
  .spot p { margin: 0 0 12px; font-size: .98rem; }
  .stamp {
    background: var(--accent); color: var(--bg); border: 2px solid var(--accent); border-radius: 999px;
    font: 600 .95rem var(--body); padding: 12px 20px; min-height: 44px; cursor: pointer;
    transition: background .2s ease, color .2s ease, border-color .2s ease, transform .15s ease;
  }
  .stamp:hover { transform: translateY(-1px); filter: brightness(1.08); }
  .stamp.stamped {
    background: transparent;
    color: var(--ink);
    border-color: var(--accent);
  }
  .stamp.stamped:hover {
    background: var(--panel);
    color: var(--accent);
  }

  /* Passport */
  .passport { margin-top: 40px; text-align: center; }
  .passport h2 { font-family: var(--display); font-size: 1.2rem; margin: 0 0 10px; }
  .badges { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }
  .badge {
    width: 56px; height: 56px; border-radius: 50%; display: grid; place-items: center;
    border: 2px dashed var(--ink); opacity: .45; font-size: .7rem; font-weight: 600;
    transition: all .4s; background: none; color: var(--ink); cursor: pointer; font-family: var(--body);
  }
  .badge:hover { opacity: .85; transform: scale(1.06); }
  .badge.got { opacity: 1; border-style: solid; background: var(--accent); color: var(--bg); border-color: var(--accent); }

  footer { margin-top: 40px; font-size: .85rem; opacity: .75; text-align: center; }

  :focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
  @media (prefers-reduced-motion: reduce) {
    * { transition: none !important; }
  }
</style>
</head>
<body>
<main>
  <header><p>Fort Canning Park, Singapore</p></header>

  <section class="hero" aria-label="Time dial">
    <svg class="dial" viewBox="0 0 200 200" aria-hidden="true">
      <g class="ring" id="ring">
        <circle cx="100" cy="100" r="92" stroke-width="2"/>
        <circle cx="100" cy="100" r="76" stroke-width="1" stroke-dasharray="2 6"/>
        <line x1="100" y1="8" x2="100" y2="24" stroke-width="3"/>
        <line x1="192" y1="100" x2="176" y2="100" stroke-width="3"/>
        <line x1="100" y1="192" x2="100" y2="176" stroke-width="3"/>
        <line x1="8" y1="100" x2="24" y2="100" stroke-width="3"/>
      </g>
      <line class="hand" x1="100" y1="100" x2="100" y2="38"/>
      <circle class="dot" cx="100" cy="100" r="7"/>
    </svg>
    <div class="year" id="year">1300s</div>
    <p class="era-name" id="eraName">Forbidden Hill</p>
  </section>

  <section class="slider-wrap" aria-label="Choose an era">
    <label for="slider" class="visually-hidden" style="position:absolute;left:-9999px">Era</label>
    <input type="range" id="slider" min="0" max="4" step="1" value="0">
    <div class="stops" id="stops"></div>
  </section>

  <article id="story" aria-live="polite"></article>

  <section class="passport" aria-label="Time passport">
    <h2>Your time passport</h2>
    <div class="badges" id="badges"></div>
  </section>

  <footer>
    Stories are simplified for visitors. Confirm opening hours and trail details with NParks and on-site signs.
  </footer>
</main>

<script>
  // ---- 1. Content: edit this to change the experience ----
  const ERAS = [
    {
      short: "1300s", year: "1300s", name: "Forbidden Hill",
      title: "A hill for kings",
      story: [
        "Long before modern Singapore, this hill overlooked the trading port of Temasek. Malay histories say it was a royal ground, and locals kept away from it. That is how it came to be called Forbidden Hill.",
        "Imagine the slope covered in forest, with the river and the sea in view below."
      ],
      spot: { id: "keramat", label: "Keramat", place: "Keramat Iskandar Shah",
        tip: "Find this shrine near the hill's summit. By tradition it marks the resting place of Iskandar Shah, the last ruler of Temasek." },
      colors: { bg: "#14281f", ink: "#f1e7c8", accent: "#e0b84a" }
    },
    {
      short: "1819", year: "1819", name: "Government Hill",
      title: "A new British settlement",
      story: [
        "In 1819 Stamford Raffles arrived and Singapore became a British trading post. The hill was chosen for the first government buildings and Raffles' residence, so it became known as Government Hill.",
        "Raffles also set up an experimental botanical garden on the slope to test crops such as nutmeg and clove."
      ],
      spot: { id: "spice", label: "Spice", place: "Raffles Garden and Spice Garden",
        tip: "Walk the Spice Garden and look for nutmeg, clove, and other plants like those once trialled here." },
      colors: { bg: "#123247", ink: "#eaf3f2", accent: "#8fd3c7" }
    },
    {
      short: "1861", year: "1861", name: "Fort Canning",
      title: "A fort above the harbour",
      story: [
        "In the 1850s and 60s the government moved down the hill and a fort was built on top. It was named after Viscount Canning, then Governor-General of India.",
        "Soldiers lived in barracks here, and the hill became a military site for the next century."
      ],
      spot: { id: "gate", label: "Gate", place: "Fort Gate and old fort walls",
        tip: "Look for the gothic-style fort gate and the stretches of old wall. Run your hand along the brickwork." },
      colors: { bg: "#3f2420", ink: "#f6eadf", accent: "#f0c987" }
    },
    {
      short: "1942", year: "1942", name: "The Battle Box",
      title: "Command centre underground",
      story: [
        "Beneath the hill, a network of bunkers served as the British command centre during the Battle of Singapore in early 1942.",
        "Key decisions were made here as the situation worsened, and the fall of Singapore followed in February. Today the Battle Box is a museum, so you can step inside."
      ],
      spot: { id: "battlebox", label: "Box", place: "The Battle Box",
        tip: "Join the guided tour to walk the corridors and rooms. Check ticket details before you go." },
      colors: { bg: "#232427", ink: "#e8e8e2", accent: "#ffb000" }
    },
    {
      short: "Today", year: "Today", name: "Park of many layers",
      title: "Four eras under your feet",
      story: [
        "Now the hill is a green park used for picnics, concerts, and heritage walks. Every path you take crosses layers of the stories you just travelled through.",
        "Take a moment at the top. You are standing where kings, traders, soldiers, and gardeners stood before you."
      ],
      spot: { id: "green", label: "Lawn", place: "Fort Canning Green",
        tip: "Sit on the lawn and look back downhill. Spot the city skyline, then picture the forest again." },
      colors: { bg: "#e6eede", ink: "#1b2b1e", accent: "#2d7a4d" }
    }
  ];

  // ---- 2. State and storage (safe if storage is blocked) ----
  const KEY = "fcTimePassport";
  let visited = [];
  try { visited = JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) {}
  function save() { try { localStorage.setItem(KEY, JSON.stringify(visited)); } catch (e) {} }

  // ---- 3. Elements ----
  const $ = id => document.getElementById(id);
  const slider = $("slider"), stops = $("stops"), story = $("story");
  const root = document.documentElement.style;

  // Era buttons under slider
  ERAS.forEach((era, i) => {
    const b = document.createElement("button");
    b.textContent = era.short;
    b.addEventListener("click", () => { slider.value = i; render(i); });
    stops.appendChild(b);
  });

  // ---- 4. Render ----
  function render(i) {
    const era = ERAS[i];
    root.setProperty("--bg", era.colors.bg);
    root.setProperty("--ink", era.colors.ink);
    root.setProperty("--accent", era.colors.accent);
    $("year").textContent = era.year;
    $("eraName").textContent = era.name;
    $("ring").style.transform = "rotate(" + (i * 72) + "deg)";
    [...stops.children].forEach((b, n) => b.setAttribute("aria-current", n === i));

    const done = visited.includes(era.spot.id);
    story.innerHTML =
      "<h2>" + era.title + "</h2>" +
      era.story.map(p => "<p>" + p + "</p>").join("") +
      '<div class="spot"><h3>Find it on site: ' + era.spot.place + "</h3>" +
      "<p>" + era.spot.tip + "</p>" +
      '<button class="stamp' + (done ? " stamped" : "") + '" id="stampBtn" title="' + (done ? "Click to unstamp" : "Click to stamp") + '">' +
      (done ? "✓ Stamped · Click to unstamp" : "Stamp my passport") + "</button></div>";

    const btn = $("stampBtn");
    btn.addEventListener("click", () => {
      if (done) {
        visited = visited.filter(id => id !== era.spot.id);
      } else {
        visited.push(era.spot.id);
      }
      save();
      render(i);
      renderBadges();
    });
  }

  function renderBadges() {
    $("badges").innerHTML = ERAS.map((e, idx) =>
      '<button type="button" class="badge' + (visited.includes(e.spot.id) ? " got" : "") +
      '" title="' + e.spot.place + (visited.includes(e.spot.id) ? " (Stamped - click to view)" : " (Click to view)") +
      '" data-idx="' + idx + '">' + e.spot.label + "</button>").join("");

    $("badges").querySelectorAll(".badge").forEach(b => {
      b.addEventListener("click", () => {
        const idx = +b.getAttribute("data-idx");
        slider.value = idx;
        render(idx);
      });
    });
  }

  slider.addEventListener("input", () => render(+slider.value));
  render(0);
  renderBadges();
</script>
</body>
</html>
```

## How to customise

- **Change the stories:** edit the `ERAS` array in the script. Each era has a year, title, story paragraphs, an on-site spot, and three colours.
- **Add an era:** copy one object in `ERAS`, then raise the slider `max` to match, and change `i * 72` in `render()` to `i * (360 / ERAS.length)`.
- **Change the look:** colours live in each era's `colors`. Fonts are set in the Google Fonts link and the `--display` and `--body` variables.
- **Fact check before launch:** confirm names, dates, and opening hours with NParks, the National Heritage Board, or on-site signage.

## Ideas for the next version

1. **GPS "you are here":** use `navigator.geolocation` to unlock each era's story when a visitor is near its spot.
2. **Photos and audio:** add archival images and a short narration clip to each era.
3. **Augmented reality:** link each spot to a WebAR scene that shows how the place looked in that era.
4. **Languages:** add English, Chinese, Malay, and Tamil text using a `lang` switcher.
5. **Quiz at the end:** award a final badge when all five spots are stamped.
