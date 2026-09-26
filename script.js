const CSV_PATH = location.pathname.includes("/sections/")
  ? "../data/posts.csv"
  : "data/posts.csv";

const CATEGORY_TREE = [
  {
    name: "literatura",
    children: [
      {
        name: "artículo",
        children: ["opinión", "divulgación", "análisis"]
      },
      {
        name: "narrativa",
        children: ["microrrelato"]
      },
      {
        name: "teatro",
        children: ["sketch"]
      },
      "traducción",
      "poesía",
      "substack",
      "experimental"
    ]
  },
  {
    name: "galería",
    children: ["photoedit", "zine", "cómic", "rpg"]
  },
  "podcast",
  {
    name: "vídeo",
    children: ["falso documental"]
  },
  {
    name: "tecnología",
    children: ["ia"]
  },
  {
    name: "géneros",
    children: [
      "memoria",
      "distopía",
      "comedia",
      "fantasía",
      "ciencia ficción",
      "realismo mágico"
    ]
  },
  "matemáticas",
  "filosofía",
  "cocina",
];

function slugify(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/&/g, "y")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function flattenCategories(nodes, result = []) {
  nodes.forEach(node => {
    const item = typeof node === "string" ? { name: node } : node;
    result.push(item.name);
    if (item.children) flattenCategories(item.children, result);
  });
  return result;
}

const CATEGORY_LABELS = Object.fromEntries(
  flattenCategories(CATEGORY_TREE).map(name => [slugify(name), name])
);

const CATEGORY_SYMBOLS = {
  literatura: "¶", galería: "▧", podcast: "∿", vídeo: "▷", tecnología: "⌘",
  géneros: "◇", matemáticas: "∑", filosofía: "φ", cocina: "⌂", artículo: "§",
  opinión: "!", divulgación: "?", análisis: "∴", narrativa: "≋", microrrelato: "·",
  teatro: "⌜", sketch: "⌞", traducción: "↔", poesía: "※", substack: "≡",
  experimental: "⌬", photoedit: "◫", zine: "▤", cómic: "▥", rpg: "⌗",
  "falso documental": "⊙", ia: "λ", memoria: "⌇", distopía: "⊘", comedia: "⌣",
  fantasía: "⋄", "ciencia ficción": "⋈", "realismo mágico": "∞"
};

const BOOK_COLORS = ["#59423d", "#384b50", "#5c5036", "#42465d", "#594454", "#603f36", "#385149", "#66513b"];

function bookColor(title) {
  let hash = 5381;
  for (const char of String(title || "")) hash = (Math.imul(hash, 33) ^ char.charCodeAt(0)) >>> 0;
  return BOOK_COLORS[hash % BOOK_COLORS.length];
}

let bookMeasureContext;
const bookDimensionCache = new Map();

function bookDimensions(title, preferredHeight, fontSize = 14.4, reserveSymbolSquare = true) {
  const cacheKey = `${title}\u0000${preferredHeight}\u0000${fontSize}\u0000${reserveSymbolSquare}`;
  if (bookDimensionCache.has(cacheKey)) return bookDimensionCache.get(cacheKey);
  if (bookMeasureContext === undefined) bookMeasureContext = document.createElement("canvas").getContext("2d");
  const context = bookMeasureContext;
  if (!context) return { width: 53, height: preferredHeight, symbolZone: reserveSymbolSquare ? 53 : 0 };
  context.font = `${fontSize}px "EB Garamond", Georgia, serif`;
  const words = String(title).split(/\s+/);
  const longestWord = Math.max(...words.map(word => context.measureText(word).width), 0);
  const titleWidth = context.measureText(title).width;
  const baseReservedHeight = reserveSymbolSquare ? 36 + 53 : 51;
  const targetSpineLength = Math.max(70, preferredHeight - baseReservedHeight);
  const columns = Math.max(1, Math.ceil(titleWidth / targetSpineLength) + 1);
  const width = Math.max(53, columns * 16 + 12);
  const symbolZone = width > 60 ? 30 : width;
  const reservedHeight = reserveSymbolSquare ? 36 + symbolZone : 51;
  const height = Math.max(
    preferredHeight,
    Math.ceil(longestWord + reservedHeight),
    Math.ceil(targetSpineLength + reservedHeight)
  );
  const dimensions = { width, height, symbolZone };
  bookDimensionCache.set(cacheKey, dimensions);
  return dimensions;
}

function categorySymbol(category) {
  return CATEGORY_SYMBOLS[String(category).toLowerCase()] || "·";
}

function parseCSV(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"' && quoted && next === '"') {
      cell += '"';
      i++;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i++;
      row.push(cell);
      if (row.some(Boolean)) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  row.push(cell);
  if (row.some(Boolean)) rows.push(row);

  const headers = rows.shift().map(h => h.trim());

  return rows.map((values, index) => {
    const item = { __index: index };
    headers.forEach((header, i) => {
      item[header] = values[i] ? values[i].trim() : "";
    });
    return item;
  });
}

function parseTags(raw) {
  if (!raw) return [];

  const cleaned = raw.trim();

  try {
    const parsed = JSON.parse(cleaned.replaceAll("'", '"'));
    return Array.isArray(parsed) ? parsed.map(String).filter(Boolean) : [];
  } catch {
    return cleaned
      .replace(/^\[|\]$/g, "")
      .split(",")
      .map(tag => tag.replace(/^["']|["']$/g, "").trim())
      .filter(Boolean);
  }
}

function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value) {
  const date = parseDate(value);
  if (!date) return "";

  return new Intl.DateTimeFormat("es", {
    year: "numeric",
    month: "short",
    day: "2-digit"
  }).format(date);
}

function sortedPosts(posts) {
  return [...posts].sort((a, b) => {
    const dateA = parseDate(a.date);
    const dateB = parseDate(b.date);

    if (dateA && dateB) return dateB - dateA;
    if (dateA && !dateB) return -1;
    if (!dateA && dateB) return 1;

    return a.__index - b.__index;
  });
}

function countByCategory(posts) {
  const counts = {};

  posts.forEach(post => {
    const uniqueTags = new Set(parseTags(post.tags).map(slugify));
    uniqueTags.forEach(tag => {
      counts[tag] = (counts[tag] || 0) + 1;
    });
  });

  return counts;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function imageFallback(title) {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
      <rect width="800" height="600" fill="#171717"/>
      <path d="M80 420 L270 170 L430 360 L520 260 L720 420" fill="none" stroke="#0D9488" stroke-width="6"/>
      <text x="80" y="510" fill="#FFFFFF" font-family="monospace" font-size="34">${escapeHtml(title)}</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function currentCategory() {
  const value = slugify(decodeURIComponent(location.hash.replace("#", "")));
  return ["archivo", "nuevos", "favoritos"].includes(value) ? "" : value;
}

function currentFeaturedFilter() {
  const value = slugify(decodeURIComponent(location.hash.replace("#", "")));
  if (value === "nuevos") return "new";
  if (value === "favoritos") return "favorites";
  return "";
}

function homeArchiveHref(hash = "") {
  const nested = location.pathname.includes("/sections/") || location.pathname.includes("/documents/");
  const base = nested ? "../index.html" : "";
  return `${base}${hash ? `#${hash}` : "#archivo"}`;
}

function articleCard(post) {
  const tags = parseTags(post.tags);
  const title = post.title || "Sin título";
  const link = post.link || "#";
  const description = post.description || "";
  const date = formatDate(post.date);

  const pipPatterns = {
    1: ["center"],
    2: ["top-left", "bottom-right"],
    3: ["top-left", "center", "bottom-right"],
    4: ["top-left", "top-right", "bottom-left", "bottom-right"],
    5: ["top-left", "top-right", "center", "bottom-left", "bottom-right"],
    6: ["top-left", "middle-left", "bottom-left", "top-right", "middle-right", "bottom-right"]
  };
  const pattern = pipPatterns[tags.length] || pipPatterns[6] || [];
  const tagLinks = tags.map((tag, index) => {
    const slug = slugify(tag);
    const categoryLabel = String(tag).toLocaleLowerCase("es");
    const pipClass = pattern[index] ? `symbol-pip-${pattern[index]}` : "symbol-pip-extra";
    return `<a class="book-symbol ${pipClass}" data-category="${escapeHtml(categoryLabel)}" aria-label="Categoría: ${escapeHtml(categoryLabel)}" title="${escapeHtml(categoryLabel)}" href="${homeArchiveHref(slug)}">${categorySymbol(tag)}</a>`;
  }).join("");

  const { width, height, symbolZone } = bookDimensions(title, 190 + ((post.__index * 37) % 90));

  return `
    <article class="archive-book" data-id="${escapeHtml(String(post.id || ""))}" style="--book-color:${bookColor(title)};--book-height:${height}px;--book-width:${width}px;--symbol-zone:${symbolZone}px">
      <button class="archive-book-link" type="button" aria-label="Seleccionar ${escapeHtml(title)}" title="${escapeHtml(title)}${description ? ` — ${escapeHtml(description)}` : ""}">
        <span class="archive-book-title">${escapeHtml(title)}</span>
      </button>
      ${tagLinks ? `<div class="book-symbols${width > 60 ? " wide-symbols" : ""}" data-count="${tags.length}">${tagLinks}</div>` : ""}
    </article>
  `;
}

function categoryMatches(post, category) {
  return parseTags(post.tags).some(tag => slugify(tag) === category);
}

function treePrefix(ancestors, isLast) {
  const ancestorBranches = ancestors.map(hasFollowingSibling => hasFollowingSibling ? "│  " : "   ").join("");
  return `${ancestorBranches}${isLast ? "└─" : "├─"}`;
}

function renderCategoryTree(posts) {
  const container = document.querySelector("#category-tree");
  const total = document.querySelector("#count-all");

  if (!container) return;

  const counts = countByCategory(posts);
  if (total) total.textContent = `(${posts.length})`;

  function renderNodes(nodes, ancestors = []) {
    return nodes.map((node, index) => {
      const item = typeof node === "string" ? { name: node } : node;
      const slug = slugify(item.name);
      const count = counts[slug] || 0;
      const hasChildren = Array.isArray(item.children) && item.children.length > 0;
      const isLast = index === nodes.length - 1;
      const childId = `tree-${slug}`;
      const prefix = treePrefix(ancestors, isLast);

      return `
        <div class="tree-node" data-slug="${slug}">
          <div class="tree-row">
            <span class="tree-prefix">${prefix}</span>
            ${hasChildren
          ? `<button class="tree-toggle" type="button" aria-expanded="false" aria-controls="${childId}" data-target="${childId}"></button>`
          : `<span class="tree-spacer"></span>`
        }
            <a class="tree-link bracket-link" href="${homeArchiveHref(slug)}">
              <span class="tree-symbol" aria-hidden="true">${categorySymbol(item.name)}</span>
              <span class="tree-label">${escapeHtml(item.name)}</span>
              <span class="tree-count">(${count})</span>
            </a>
          </div>

          ${hasChildren
          ? `<div class="tree-children" id="${childId}" hidden>${renderNodes(item.children, [...ancestors, !isLast])}</div>`
          : ""
        }
        </div>
      `;
    }).join("");
  }

  container.innerHTML = renderNodes(CATEGORY_TREE);

  container.querySelectorAll(".tree-toggle").forEach(button => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.target);
      const expanded = button.getAttribute("aria-expanded") === "true";

      button.setAttribute("aria-expanded", String(!expanded));
      if (target) target.hidden = expanded;
    });
  });
}

const OBJECT_ART = {
  portrait: `<svg viewBox="0 0 88 132" role="img" aria-label="Retrato enmarcado">
    <path d="M8 8h72v116H8z" fill="#171310" stroke="#9a7850" stroke-width="3"/><path d="M13 13h62v106H13z" fill="#30241b" stroke="#4c3928" stroke-width="2"/>
    <path d="M18 18h52v96H18z" fill="#252b2c" stroke="#b59a69" stroke-width="1.5"/>
    <path d="M18 81q26-22 52 0v33H18z" fill="#5b5146"/><path d="M28 47a16 16 0 1 1 32 0v8H28z" fill="#807767"/><ellipse cx="44" cy="48" rx="11" ry="14" fill="#a89b82"/>
    <path d="M21 27h12M55 27h12M21 106h12M55 106h12" stroke="#c3a974" stroke-width="1" opacity=".65"/>
  </svg>`,
  music: `<svg viewBox="0 0 104 132" role="img" aria-label="Tocadiscos">
    <rect x="6" y="20" width="92" height="105" rx="5" fill="#38251a" stroke="#a27b4d" stroke-width="2.5"/><path d="M10 26h84v72H10z" fill="#151617" stroke="#60462f"/>
    <circle cx="49" cy="61" r="30" fill="#090a0b" stroke="#88714c" stroke-width="1.5"/><circle cx="49" cy="61" r="25" fill="none" stroke="#393a39"/><circle cx="49" cy="61" r="19" fill="none" stroke="#323333"/><circle cx="49" cy="61" r="13" fill="none" stroke="#383938"/><circle cx="49" cy="61" r="7" fill="#a67848"/><circle cx="49" cy="61" r="2" fill="#e4d7b5"/>
    <circle cx="81" cy="35" r="5" fill="#a9a79b" stroke="#514b40" stroke-width="2"/><path d="M81 39 70 81l-5 3" fill="none" stroke="#c2c0b5" stroke-width="3" stroke-linecap="round"/><path d="M67 84h10v5H67z" fill="#71624d"/>
    <path d="M16 107h72" stroke="#725439"/><circle cx="23" cy="114" r="3" fill="#c19b63"/><rect x="34" y="111" width="29" height="5" rx="2" fill="#77756d"/><circle cx="81" cy="114" r="3" fill="#d8b56e"/>
  </svg>`,
  travel: `<svg viewBox="0 0 104 132" role="img" aria-label="Globo terráqueo">
    <path d="M51 8c-19 0-35 16-35 36s16 35 35 35 35-15 35-35S70 8 51 8z" fill="#213638" stroke="#b9a574" stroke-width="2"/>
    <path d="M25 30q26 11 52 0M18 45q33 12 66 0M27 62q24-11 49 0M51 10q-17 34 0 67M51 10q17 34 0 67" fill="none" stroke="#78908a" stroke-width="1" opacity=".68"/>
    <path d="m30 27 8-8 8 3-2 8 5 5-5 9-9-2-5 7-6-5 1-9zM59 45l7-4 7 5-3 8-7 6-5-6zM43 62l7 1 3 7-6 5-5-6z" fill="#8d9270" stroke="#b4a574" stroke-width=".7"/>
    <path d="M17 43c0 21 15 36 34 36s34-15 34-36M51 78v29M36 108h30l-5 8H41z" fill="none" stroke="#8c744d" stroke-width="3" stroke-linecap="round"/>
    <path d="M28 120h46" stroke="#b9a574" stroke-width="3" stroke-linecap="round"/>
  </svg>`,
  quotes: `<svg viewBox="0 0 100 132" role="img" aria-label="Nota y pluma">
    <path d="m10 31 56-12 20 94-56 12z" fill="#bcb099" stroke="#8d7958" stroke-width="2"/><path d="m18 43 49-10M21 57l49-10M24 71l49-10M27 85l49-10M30 99l49-10" stroke="#827965" stroke-width="1" opacity=".7"/>
    <path d="M20 39 27 38M28 35l7-2" stroke="#eee1c5" stroke-width="2"/><path d="M28 31q7-11 15 0v10H28z" fill="#78694f"/><path d="M75 13 51 110l-7 10 1-13 24-97z" fill="#25292a" stroke="#a99b78" stroke-width="1.5"/><path d="m45 107-1 13 7-10z" fill="#c1a36d"/><path d="m72 20-14 56" stroke="#aeb1aa" stroke-width="2" opacity=".75"/>
  </svg>`,
  reading: `<svg viewBox="0 0 88 132" role="img" aria-label="Libro cerrado con marcapáginas">
    <path d="M17 25q0-7 8-9l43-7q5-1 5 5v101q0 5-5 6l-44 7q-7 1-7-6z" fill="#30241d" stroke="#aa8957" stroke-width="2.5"/>
    <path d="M24 20 66 13v106l-42 7z" fill="#594233" stroke="#c0a06a" stroke-width="1.5"/>
    <path d="m24 20-7 5v97l7 4z" fill="#281e19" stroke="#705437" stroke-width="1.5"/>
    <path d="m31 31 29-5v2l-29 5zM31 105l29-5v2l-29 5z" fill="#b79a65" opacity=".8"/>
    <path d="m34 52 21-4v24l-10 7-11-4z" fill="none" stroke="#c0a06a" stroke-width="1.5"/><path d="m42 64 5 4 7-11" fill="none" stroke="#c0a06a" stroke-width="1.5"/>
    <path d="M52 8h13v66l-6.5-7-6.5 7z" fill="#713d3b" stroke="#bd8171" stroke-width="1.5"/>
    <path d="M20 31v81M70 21v81" stroke="#d2b783" stroke-width="1" opacity=".65"/>
  </svg>`,
  github: `<svg viewBox="0 0 100 132" role="img" aria-label="Disquete">
    <path d="M13 8h62l13 13v103H13z" fill="#303334" stroke="#9a9c94" stroke-width="2.5"/><path d="M27 9v37h48V9" fill="#878a84" stroke="#181a1a" stroke-width="2"/><path d="M37 14h11v23H37z" fill="#191b1b"/><path d="M23 57h56v48H23z" rx="3" fill="#c0b7a4" stroke="#716b5e" stroke-width="2"/><path d="M28 64h46" stroke="#847b69"/><text x="51" y="83" text-anchor="middle" fill="#3b3832" font-family="monospace" font-size="7">1.44 MB</text><text x="51" y="97" text-anchor="middle" fill="#3b3832" font-family="monospace" font-size="10" letter-spacing="1">GITHUB</text><path d="M19 116h63" stroke="#666a69"/>
  </svg>`,
  movies: `<svg viewBox="0 0 112 132" role="img" aria-label="Proyector de cine">
    <circle cx="32" cy="34" r="22" fill="#242626" stroke="#a29b82" stroke-width="3"/><circle cx="32" cy="34" r="13" fill="none" stroke="#6e706c" stroke-width="2"/><circle cx="32" cy="34" r="4" fill="#b9a574"/>
    <circle cx="80" cy="34" r="22" fill="#242626" stroke="#a29b82" stroke-width="3"/><circle cx="80" cy="34" r="13" fill="none" stroke="#6e706c" stroke-width="2"/><circle cx="80" cy="34" r="4" fill="#b9a574"/>
    <path d="M17 53q31-17 63 0" fill="none" stroke="#d2c497" stroke-width="2"/><rect x="17" y="57" width="72" height="45" rx="6" fill="#383b3b" stroke="#98917b" stroke-width="2"/><path d="M89 68h14l7 8-7 9H89z" fill="#656863" stroke="#a39a7f" stroke-width="2"/><circle cx="101" cy="76" r="3" fill="#d5c18b"/><circle cx="32" cy="73" r="5" fill="#9c7a4c"/><path d="M23 102v14M79 102v14M18 117h66" stroke="#777064" stroke-width="4" stroke-linecap="round"/><path d="M42 68h20M42 76h16" stroke="#a8a79d" stroke-width="1.5"/>
  </svg>`
};

const SHELF_OBJECTS = [
    ["portrait", "About", "sections/about.html"],
    ["music", "Música", "sections/music.html"],
    ["travel", "Viajes", "sections/travel.html"],
    ["quotes", "Citas", "sections/quotes.html"],
    ["reading", "Libros", "sections/books.html"],
    ["github", "Código", "sections/codigo.html"],
    ["movies", "Películas", "sections/movies.html"]
  ];

// Target book counts between object insertions. These increments leave 3–4 books
// between neighboring objects while placing all seven objects in a 30-book shelf.
const OBJECT_BOOK_GAPS = [4, 4, 4, 4, 4, 5];

function renderSectionArtwork() {
  document.querySelectorAll("[data-object-art]").forEach(container => {
    container.innerHTML = OBJECT_ART[container.dataset.objectArt] || "";
  });
}

function objectMarkup([type, label, href]) {
  const base = location.pathname.includes("/sections/") || location.pathname.includes("/documents/") ? "../" : "";
  const target = href.startsWith("http") ? href : `${base}${href}`;
  const tooltip = label.toLocaleLowerCase("es");
  return `<a class="shelf-object object-${type}" href="${target}" title="${tooltip}">
      <span class="object-tooltip">${tooltip}</span>
      <span class="object-art">${OBJECT_ART[type]}</span>
    </a>`;
}

function insertHomeObjects() {
  const sections = [...document.querySelectorAll(".library-shelf .list-stack")];
  if (!sections.length) return;

  let objectIndex = 0;
  let postCount = 0;
  sections.forEach(shelf => {
    [...shelf.querySelectorAll(":scope > .article-item")].forEach(item => {
      postCount++;
      item.style.setProperty("--book-color", bookColor(item.innerText.trim()));
      const dimensions = bookDimensions(item.innerText.trim(), item.getBoundingClientRect().height, 14.4, false);
      item.style.setProperty("--book-width", `${dimensions.width}px`);
      item.style.setProperty("--book-height", `${dimensions.height}px`);
      if (postCount % 4 === 0 && objectIndex < 4) {
        item.insertAdjacentHTML("afterend", objectMarkup(SHELF_OBJECTS[objectIndex++]));
      }
    });
  });
}

function openParentsOfActiveCategory() {
  const active = document.querySelector(".tree-link.active");
  if (!active) return;

  let parent = active.closest(".tree-children");

  while (parent) {
    parent.hidden = false;

    const button = document.querySelector(`[data-target="${parent.id}"]`);
    if (button) button.setAttribute("aria-expanded", "true");

    parent = parent.parentElement.closest(".tree-children");
  }
}

function updateActiveCategory(slug) {
  const featuredFilter = currentFeaturedFilter();
  document.querySelectorAll(".tree-link").forEach(link => {
    const linkSlug = slugify(link.hash.replace("#", ""));
    const active = link.classList.contains("feature-filter")
      ? link.dataset.filter === featuredFilter
      : link.classList.contains("category-all")
        ? !slug && !featuredFilter
        : linkSlug === slug && !featuredFilter;
    link.classList.toggle("active", active);
  });
  document.querySelector(".category-all")?.classList.toggle("active", !slug && !featuredFilter);

  openParentsOfActiveCategory();
}

function renderArchive(posts) {
  const grid = document.querySelector("#archive-grid");
  const title = document.querySelector("#archive-title");
  const count = document.querySelector("#archive-count");

  if (!grid || !title || !count) return;

  const category = currentCategory();
  const featuredFilter = currentFeaturedFilter();
  const query = (document.querySelector("#archive-search")?.value || "").trim().toLowerCase();

  const categoryFiltered = category
    ? posts.filter(post => categoryMatches(post, category))
    : posts;
  let filtered = query
    ? categoryFiltered.filter(post => [post.title, post.date, post.description, ...parseTags(post.tags)].join(" ").toLowerCase().includes(query))
    : categoryFiltered;

  if (featuredFilter) {
    const filterLink = document.querySelector(`.feature-filter[data-filter="${featuredFilter}"]`);
    const configuredIds = (filterLink?.dataset.postIds || "").split(",").map(id => id.trim()).filter(Boolean);
    let ids = configuredIds;
    if (!ids.length && featuredFilter === "new") {
      ids = [...posts]
        .sort((a, b) => Number(b.id) - Number(a.id))
        .slice(0, 8)
        .map(post => String(post.id));
    } else if (!ids.length && featuredFilter === "favorites") {
      ids = ["61", "37", "52", "59", "50", "49", "32", "51"];
    }
    const idSet = new Set(ids);
    filtered = filtered.filter(post => idSet.has(String(post.id)));
  }

  const label = CATEGORY_LABELS[category] || category;

  title.textContent = category ? label : featuredFilter === "new" ? "Nuevos" : featuredFilter === "favorites" ? "Favoritos" : "Todo";
  count.textContent = `${filtered.length} archivo${filtered.length === 1 ? "" : "s"}`;

  updateActiveCategory(category);

  if (!filtered.length) {
    grid.innerHTML = `<p class="panel">No hay archivos para esta categoría.</p>`;
    return;
  }

  const showObjects = filtered.length >= 30;
  const shelfPadding = window.matchMedia("(max-width: 520px)").matches ? 20 : 36;
  const availableWidth = Math.max(1, grid.clientWidth - shelfPadding);
  const objectWidth = window.matchMedia("(max-width: 520px)").matches
    ? 54
    : Math.max(58, Math.min(82, window.innerWidth * .07));
  const gap = 5;
  const shelves = [];
  let shelfContents = "";
  let shelfWidth = 0;
  let shelfItems = 0;
  let objectIndex = 0;
  let nextObjectThreshold = OBJECT_BOOK_GAPS[0];

  filtered.forEach((post, index) => {
    const title = post.title || "Sin título";
    const dimensions = bookDimensions(title, 190 + ((post.__index * 37) % 90));
    const globalBookNumber = index + 1;
    const hasObject = showObjects && objectIndex < SHELF_OBJECTS.length && globalBookNumber >= nextObjectThreshold;
    const itemWidth = dimensions.width + (hasObject ? gap + objectWidth : 0) + (shelfItems ? gap : 0);

    if (shelfItems && shelfWidth + itemWidth > availableWidth) {
      shelves.push(`<section class="archive-shelf"><div class="archive-books">${shelfContents}</div><div class="archive-plank" aria-hidden="true"></div></section>`);
      shelfContents = "";
      shelfWidth = 0;
      shelfItems = 0;
    }

    shelfContents += articleCard(post);
    shelfWidth += dimensions.width;
    shelfItems++;
    if (shelfItems > 1) shelfWidth += gap;

    if (hasObject) {
      shelfContents += objectMarkup(SHELF_OBJECTS[objectIndex++]);
      shelfWidth += objectWidth + gap;
      shelfItems++;
      nextObjectThreshold += OBJECT_BOOK_GAPS[objectIndex % OBJECT_BOOK_GAPS.length];
    }
  });

  if (shelfContents) {
    shelves.push(`<section class="archive-shelf"><div class="archive-books">${shelfContents}</div><div class="archive-plank" aria-hidden="true"></div></section>`);
  }

  grid.innerHTML = shelves.join("");
}

async function initArchive() {
  const grid = document.querySelector("#archive-grid");
  const detail = document.querySelector("#book-detail");

  try {
    const response = await fetch(CSV_PATH);
    if (!response.ok) throw new Error(`No se pudo cargar ${CSV_PATH}`);

    const text = await response.text();
    const posts = sortedPosts(parseCSV(text));

    renderCategoryTree(posts);
    renderArchive(posts);

    let selectedBook = null;
    function selectBook(post) {
      if (!post || !detail) return;
      selectedBook = post;
      grid.querySelectorAll(".archive-book.chosen").forEach(book => book.classList.remove("chosen"));
      const bookElement = grid.querySelector(`.archive-book[data-id="${CSS.escape(String(post.id || ""))}"]`);
      bookElement?.classList.add("chosen");
      const tags = parseTags(post.tags);
      detail.innerHTML = `
        <button class="book-detail-close" type="button" aria-label="Cerrar">×</button>
        <h2>${escapeHtml(post.title || "Sin título")}</h2>
        <p class="book-detail-description">${escapeHtml(post.description || "Sin descripción.")}</p>
        ${tags.length ? `<div class="book-detail-tags" aria-label="Categorías">${tags.map(tag => `<span>${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        <a class="book-detail-read" href="${escapeHtml(post.link || "#")}">Leer <span aria-hidden="true">↗</span></a>
      `;
      detail.hidden = false;
      detail.classList.add("show");
    }

    grid.addEventListener("click", event => {
      const button = event.target.closest(".archive-book-link");
      if (!button) return;
      const book = button.closest(".archive-book");
      selectBook(posts.find(post => String(post.id) === book?.dataset.id));
    });
    detail?.addEventListener("click", event => {
      if (!event.target.closest(".book-detail-close")) return;
      detail.classList.remove("show");
      detail.hidden = true;
      grid.querySelectorAll(".archive-book.chosen").forEach(book => book.classList.remove("chosen"));
      selectedBook = null;
    });

    document.querySelector("#archive-search")?.addEventListener("input", rerenderArchive);
    document.querySelectorAll(".feature-filter").forEach(link => {
      link.addEventListener("click", event => {
        event.preventDefault();
        if (location.hash === link.hash) {
          rerenderArchive();
        } else {
          history.pushState(null, "", link.hash);
          rerenderArchive();
        }
      });
    });

    const die = document.querySelector("#die");
    if (die) {
      let spinTimer;
      let pickTimer;
      const faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];

      die.addEventListener("click", () => {
        const books = [...document.querySelectorAll("#archive-grid .archive-book")];
        if (!books.length) return;

        clearInterval(spinTimer);
        clearTimeout(pickTimer);
        die.classList.remove("roll");
        void die.offsetWidth;
        die.classList.add("roll");

        let ticks = 0;
        spinTimer = setInterval(() => {
          die.textContent = faces[Math.floor(Math.random() * faces.length)];
          if (++ticks >= 9) clearInterval(spinTimer);
        }, 65);

        const chosen = books[Math.floor(Math.random() * books.length)];
        pickTimer = setTimeout(() => {
          clearInterval(spinTimer);
          die.textContent = faces[Math.floor(Math.random() * faces.length)];
          books.forEach(book => book.classList.remove("chosen"));
          const chosenPost = posts.find(post => String(post.id) === chosen.dataset.id);
          if (chosenPost) selectBook(chosenPost);
          chosen.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });

        }, 720);
      });
    }

    function rerenderArchive() {
      renderArchive(posts);
      if (selectedBook && !grid.querySelector(`.archive-book[data-id="${CSS.escape(String(selectedBook.id || ""))}"]`)) {
        detail?.classList.remove("show");
        if (detail) detail.hidden = true;
        selectedBook = null;
      } else if (selectedBook) {
        selectBook(selectedBook);
      }
    }

    window.addEventListener("hashchange", rerenderArchive);
    window.addEventListener("popstate", rerenderArchive);
    let resizeTimer;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(rerenderArchive, 120);
    });
  } catch (error) {
    if (grid) {
      grid.innerHTML = `
        <p class="panel">
          Error cargando el CSV. Comprueba que existe <code>${CSV_PATH}</code>
          y que se sirve desde un servidor estático.
        </p>
      `;
    }

    console.error(error);
  }
}

insertHomeObjects();
renderSectionArtwork();

if (document.body.dataset.page === "archive") {
  initArchive();
}
