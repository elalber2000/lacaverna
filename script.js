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
  return slugify(decodeURIComponent(location.hash.replace("#", "")));
}

function articleCard(post) {
  const tags = parseTags(post.tags);
  const title = post.title || "Sin título";
  const link = post.link || "#";
  const img = post.img_link || imageFallback(title);
  const description = post.description || "";
  const date = formatDate(post.date);

  const tagLinks = tags.map(tag => {
    const slug = slugify(tag);
    return `<a class="tag bracket-link" href="../sections/archive.html#${slug}">${escapeHtml(tag)}</a>`;
  }).join("");

  return `
    <article class="archive-card">
      <a href="${escapeHtml(link)}" aria-label="${escapeHtml(title)}">
        <img class="archive-image" src="${escapeHtml(img)}" alt="${escapeHtml(title)}" loading="lazy" />
      </a>

      <div class="archive-content">
        ${date ? `<div class="meta-row"><time>${date}</time></div>` : ""}

        <a href="${escapeHtml(link)}">
          <h3>${escapeHtml(title)}</h3>
        </a>

        ${description ? `<p>${escapeHtml(description)}</p>` : ""}

        <div class="tags">
          ${tagLinks}
        </div>
      </div>
    </article>
  `;
}

function categoryMatches(post, category) {
  return parseTags(post.tags).some(tag => slugify(tag) === category);
}

function treePrefix(level, isLast) {
  if (level === 0) return isLast ? "└─" : "├─";
  return `${"│   ".repeat(level)}${isLast ? "└─" : "├─"}`;
}

function renderCategoryTree(posts) {
  const container = document.querySelector("#category-tree");
  const total = document.querySelector("#count-all");

  if (!container) return;

  const counts = countByCategory(posts);
  if (total) total.textContent = `(${posts.length})`;

  function renderNodes(nodes, level = 0) {
    return nodes.map((node, index) => {
      const item = typeof node === "string" ? { name: node } : node;
      const slug = slugify(item.name);
      const count = counts[slug] || 0;
      const hasChildren = Array.isArray(item.children) && item.children.length > 0;
      const isLast = index === nodes.length - 1;
      const childId = `tree-${slug}`;
      const prefix = treePrefix(level, isLast);

      return `
        <div class="tree-node" data-slug="${slug}">
          <div class="tree-row">
            <span class="tree-prefix">${prefix}</span>
            ${hasChildren
          ? `<button class="tree-toggle" type="button" aria-expanded="false" aria-controls="${childId}" data-target="${childId}"></button>`
          : `<span class="tree-spacer"></span>`
        }
            <a class="tree-link bracket-link" href="archive.html#${slug}">
              ${escapeHtml(item.name)} <span>(${count})</span>
            </a>
          </div>

          ${hasChildren
          ? `<div class="tree-children" id="${childId}" hidden>${renderNodes(item.children, level + 1)}</div>`
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
  document.querySelectorAll(".tree-link").forEach(link => {
    const linkSlug = slugify(link.hash.replace("#", ""));
    link.classList.toggle("active", linkSlug === slug);
  });

  openParentsOfActiveCategory();
}

function renderArchive(posts) {
  const grid = document.querySelector("#archive-grid");
  const title = document.querySelector("#archive-title");
  const count = document.querySelector("#archive-count");

  if (!grid || !title || !count) return;

  const category = currentCategory();

  const filtered = category
    ? posts.filter(post => categoryMatches(post, category))
    : posts;

  const label = CATEGORY_LABELS[category] || category;

  title.textContent = category ? label : "Todo";
  count.textContent = `${filtered.length} archivo${filtered.length === 1 ? "" : "s"}`;

  updateActiveCategory(category);

  grid.innerHTML = filtered.length
    ? filtered.map(articleCard).join("")
    : `<p class="panel">No hay archivos para esta categoría.</p>`;
}

async function initArchive() {
  const grid = document.querySelector("#archive-grid");

  try {
    const response = await fetch(CSV_PATH);
    if (!response.ok) throw new Error(`No se pudo cargar ${CSV_PATH}`);

    const text = await response.text();
    const posts = sortedPosts(parseCSV(text));

    renderCategoryTree(posts);
    renderArchive(posts);

    window.addEventListener("hashchange", () => renderArchive(posts));
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

if (document.body.dataset.page === "archive") {
  initArchive();
}