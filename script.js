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
const CATEGORY_INFO = new Map();

function indexCategories(nodes, depth = 0) {
  nodes.forEach(node => {
    const item = typeof node === "string" ? { name: node } : node;
    CATEGORY_INFO.set(slugify(item.name), { depth, order: CATEGORY_INFO.size });
    if (item.children) indexCategories(item.children, depth + 1);
  });
}

indexCategories(CATEGORY_TREE);

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

const BOOKS_DIRECTORY = location.pathname.includes("/sections/")
  ? "../assets/books/"
  : "assets/books/";
let BOOK_IMAGES = [];

async function discoverBookImages() {
  const response = await fetch(BOOKS_DIRECTORY);
  if (!response.ok) throw new Error(`No se pudo cargar ${BOOKS_DIRECTORY}`);

  const directory = new DOMParser().parseFromString(await response.text(), "text/html");
  return [...directory.querySelectorAll("a[href]")]
    .map(link => link.getAttribute("href"))
    .filter(href => href && href.toLowerCase().endsWith(".svg"))
    .map(href => new URL(href, new URL(BOOKS_DIRECTORY, document.baseURI)).href);
}

function bookImage(title) {
  let hash = 5381;
  for (const char of String(title || "")) hash = (Math.imul(hash, 33) ^ char.charCodeAt(0)) >>> 0;
  return BOOK_IMAGES[hash % BOOK_IMAGES.length];
}

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
  const width = Math.max(57, columns * 16 + 16);
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

function primaryCategory(tags) {
  return [...tags]
    .sort((a, b) => {
      const infoA = CATEGORY_INFO.get(slugify(a));
      const infoB = CATEGORY_INFO.get(slugify(b));
      const depthA = infoA?.depth ?? -1;
      const depthB = infoB?.depth ?? -1;
      if (depthA !== depthB) return depthB - depthA;
      return (infoA?.order ?? Number.POSITIVE_INFINITY) - (infoB?.order ?? Number.POSITIVE_INFINITY);
    })[0] || "";
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

  const tag = primaryCategory(tags);
  const tagLinks = tag ? (() => {
    const slug = slugify(tag);
    const categoryLabel = String(tag).toLocaleLowerCase("es");
    return `<a class="book-symbol symbol-pip-center" data-category="${escapeHtml(categoryLabel)}" aria-label="Categoría principal: ${escapeHtml(categoryLabel)}" title="${escapeHtml(categoryLabel)}" href="${homeArchiveHref(slug)}">${categorySymbol(tag)}</a>`;
  })() : "";

  const { width, height, symbolZone } = bookDimensions(title, 190 + ((post.__index * 37) % 90));
  const image = bookImage(title);

  return `
    <article class="archive-book" data-id="${escapeHtml(String(post.id || ""))}" style="--book-color:${bookColor(title)};--book-height:${height}px;--book-width:${width}px;--symbol-zone:${symbolZone}px">
      <img class="archive-book-image" src="${image}" alt="" aria-hidden="true">
      <button class="archive-book-link" type="button" aria-label="Seleccionar ${escapeHtml(title)}">
        <span class="archive-book-title">${escapeHtml(title)}</span>
      </button>
      ${tagLinks ? `<div class="book-symbols${width > 60 ? " wide-symbols" : ""}" data-count="1">${tagLinks}</div>` : ""}
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
  portrait: ["about.svg", "Retrato"],
  music: ["music.svg", "Tocadiscos"],
  travel: ["travel.svg", "Globo terráqueo"],
  quotes: ["quotes.svg", "Nota y pluma"],
  reading: ["books.svg", "Libro"],
  github: ["codigo.svg", "Disquete"],
  movies: ["movies.svg", "Proyector de cine"]
};

function objectImage(type) {
  const art = OBJECT_ART[type];
  if (!art) return "";
  const [file, label] = art;
  const base = location.pathname.includes("/sections/") || location.pathname.includes("/documents/") ? "../" : "";
  return `<img src="${base}assets/items/${file}" alt="${label}" loading="lazy" />`;
}

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
    container.innerHTML = objectImage(container.dataset.objectArt);
  });
}

function objectMarkup([type, label, href]) {
  const base = location.pathname.includes("/sections/") || location.pathname.includes("/documents/") ? "../" : "";
  const target = href.startsWith("http") ? href : `${base}${href}`;
  const tooltip = label.toLocaleLowerCase("es");
  return `<a class="shelf-object object-${type}" href="${target}">
      <span class="object-tooltip">${tooltip}</span>
      <span class="object-art">${objectImage(type)}</span>
  </a>`;
}

function rebalanceShelves(grid) {
  const shelves = [...grid.querySelectorAll(":scope > .archive-shelf")];

  for (let index = 0; index < shelves.length; index++) {
    const currentBooks = shelves[index].querySelector(".archive-books");
    if (!currentBooks) continue;

    while (currentBooks.scrollWidth > currentBooks.clientWidth + 1 && currentBooks.children.length > 1) {
      let nextShelf = shelves[index + 1];
      if (!nextShelf) {
        nextShelf = document.createElement("section");
        nextShelf.className = "archive-shelf";
        nextShelf.innerHTML = '<div class="archive-books"></div><div class="archive-plank" aria-hidden="true"></div>';
        grid.append(nextShelf);
        shelves.push(nextShelf);
      }

      const nextBooks = nextShelf.querySelector(".archive-books");
      nextBooks.prepend(currentBooks.lastElementChild);
    }
  }
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

function shelfObjectWidth(type) {
  const narrow = window.matchMedia("(max-width: 520px)").matches;
  if (narrow) {
    if (["music", "movies"].includes(type)) return 240;
    if (["travel", "reading", "quotes"].includes(type)) return 180;
    return 120;
  }

  const clamp = (min, ratio, max) => Math.max(min, Math.min(max, window.innerWidth * ratio));
  if (["music", "movies"].includes(type)) return clamp(170, .19, 262);
  if (["travel", "reading", "quotes"].includes(type)) return clamp(132, .14, 196);
  return clamp(88, .10, 138);
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
  const shelfPadding = window.matchMedia("(max-width: 520px)").matches ? 10 : 18;
  const availableWidth = Math.max(1, grid.clientWidth - shelfPadding);
  const gap = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--archive-book-gap"));
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
    const objectWidth = hasObject ? shelfObjectWidth(SHELF_OBJECTS[objectIndex][0]) : 0;
    const candidateWidth = shelfWidth
      + (shelfItems ? gap : 0)
      + dimensions.width
      + (hasObject ? gap + objectWidth : 0);

    if (shelfItems && candidateWidth > availableWidth) {
      shelves.push(`<section class="archive-shelf"><div class="archive-books">${shelfContents}</div><div class="archive-plank" aria-hidden="true"></div></section>`);
      shelfContents = "";
      shelfWidth = 0;
      shelfItems = 0;
    }

    shelfContents += articleCard(post);
    if (shelfItems) shelfWidth += gap;
    shelfWidth += dimensions.width;
    shelfItems++;

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
  rebalanceShelves(grid);
}

async function initArchive() {
  const grid = document.querySelector("#archive-grid");
  const detail = document.querySelector("#book-detail");

  try {
    const [response, bookImages] = await Promise.all([
      fetch(CSV_PATH),
      discoverBookImages()
    ]);
    if (!response.ok) throw new Error(`No se pudo cargar ${CSV_PATH}`);

    BOOK_IMAGES = bookImages;
    if (!BOOK_IMAGES.length) throw new Error("No hay imágenes de libros disponibles");

    const text = await response.text();
    const posts = sortedPosts(parseCSV(text));

    renderCategoryTree(posts);
    renderArchive(posts);

    let selectedBook = null;
    let detailHideTimer;
    const hoverTitle = document.createElement("div");
    hoverTitle.className = "archive-book-hover-title";
    hoverTitle.hidden = true;
    hoverTitle.setAttribute("role", "tooltip");
    document.body.append(hoverTitle);

    function showBookHoverTitle(book) {
      const title = book?.querySelector(".archive-book-title")?.textContent.trim();
      if (!title) return;
      hoverTitle.textContent = title;
      hoverTitle.hidden = false;
      requestAnimationFrame(() => {
        const bookRect = book.getBoundingClientRect();
        const labelRect = hoverTitle.getBoundingClientRect();
        const edge = 8;
        const left = Math.min(
          Math.max(edge + labelRect.width / 2, bookRect.left + bookRect.width / 2),
          window.innerWidth - edge - labelRect.width / 2
        );
        const above = bookRect.top - labelRect.height - 10;
        hoverTitle.style.left = `${left}px`;
        hoverTitle.style.top = `${Math.max(edge, above >= edge ? above : bookRect.bottom + 10)}px`;
      });
    }

    function hideBookHoverTitle() {
      hoverTitle.hidden = true;
    }

    function postImagePath(post) {
      const imagePath = String(post?.img_link || "").trim();
      return imagePath.startsWith("../") ? imagePath.slice(3) : imagePath;
    }

    function positionDetail(bookElement) {
      if (!bookElement || !detail) return;
      const bookRect = bookElement.getBoundingClientRect();
      const shelfRect = bookElement.closest(".archive-shelf")?.getBoundingClientRect();
      const detailRect = detail.getBoundingClientRect();
      const edge = 8;
      const left = Math.min(
        Math.max(edge, bookRect.left + (bookRect.width - detailRect.width) / 2),
        Math.max(edge, window.innerWidth - detailRect.width - edge)
      );
      const top = shelfRect
        ? shelfRect.top - detailRect.height + 18
        : bookRect.top - detailRect.height + 18;
      detail.style.left = `${left}px`;
      const maxTop = Math.max(edge, window.innerHeight - detailRect.height - edge);
      detail.style.top = `${Math.min(Math.max(edge, top), maxTop)}px`;
    }

    function selectBook(post) {
      if (!post || !detail) return;
      clearTimeout(detailHideTimer);
      selectedBook = post;
      grid.querySelectorAll(".archive-book.chosen").forEach(book => book.classList.remove("chosen"));
      const bookElement = grid.querySelector(`.archive-book[data-id="${CSS.escape(String(post.id || ""))}"]`);
      bookElement?.classList.add("chosen");
      const tags = parseTags(post.tags);
      const imagePath = postImagePath(post);
      detail.innerHTML = `
        <button class="book-detail-close" type="button" aria-label="Cerrar">×</button>
        <h2>${escapeHtml(post.title || "Sin título")}</h2>
        ${imagePath ? `<img class="book-detail-image" src="${escapeHtml(imagePath)}" alt="" aria-hidden="true">` : ""}
        <p class="book-detail-description">${escapeHtml(post.description || "Sin descripción.")}</p>
        ${tags.length ? `<div class="book-detail-tags" aria-label="Categorías">${tags.map(tag => `<span>${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        <a class="book-detail-read" href="${escapeHtml(post.link || "#")}">Leer <span aria-hidden="true">↗</span></a>
      `;
      detail.hidden = false;
      detail.classList.add("show");
      requestAnimationFrame(() => positionDetail(bookElement));
    }

    function hideDetailSoon() {
      clearTimeout(detailHideTimer);
      detailHideTimer = setTimeout(() => {
        if (detail.matches(":hover")) return;
        detail.classList.remove("show");
        detail.hidden = true;
        grid.querySelectorAll(".archive-book.chosen").forEach(book => book.classList.remove("chosen"));
        selectedBook = null;
      }, 180);
    }

    grid.addEventListener("pointerover", event => {
      const book = event.target.closest(".archive-book");
      if (!book || (event.relatedTarget && book.contains(event.relatedTarget))) return;
      showBookHoverTitle(book);
    });
    grid.addEventListener("pointerout", event => {
      const book = event.target.closest(".archive-book");
      if (book && (!event.relatedTarget || !book.contains(event.relatedTarget))) hideBookHoverTitle();
    });
    grid.addEventListener("pointerleave", () => {
      hideBookHoverTitle();
      hideDetailSoon();
    });
    grid.addEventListener("click", event => {
      const book = event.target.closest(".archive-book");
      if (!book || !event.target.closest(".archive-book-link")) return;
      selectBook(posts.find(post => String(post.id) === book.dataset.id));
    });
    grid.addEventListener("focusin", event => {
      const book = event.target.closest(".archive-book");
      if (book) {
        showBookHoverTitle(book);
        selectBook(posts.find(post => String(post.id) === book.dataset.id));
      }
    });
    grid.addEventListener("focusout", event => {
      const book = event.target.closest(".archive-book");
      if (book && (!event.relatedTarget || !book.contains(event.relatedTarget))) hideBookHoverTitle();
    });
    detail?.addEventListener("pointerenter", () => clearTimeout(detailHideTimer));
    detail?.addEventListener("pointerleave", hideDetailSoon);
    detail?.addEventListener("click", event => {
      if (!event.target.closest(".book-detail-close")) return;
      hideDetailSoon();
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
