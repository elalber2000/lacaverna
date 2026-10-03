import html
import logging
import re
import unicodedata

import requests

from utils import ROOT_PATH, atomic_write_text, configure_logging


configure_logging()

README_URL = "https://raw.githubusercontent.com/elalber2000/elalber2000/main/README.md"
CODE_PAGE = ROOT_PATH / "sections" / "codigo.html"
START = "<!-- PLACEHOLDER_START -->"
END = "<!-- PLACEHOLDER_END -->"


def remove_emoji(value):
    value = re.sub(r":[a-z0-9_+-]+:", "", value, flags=re.IGNORECASE)
    return "".join(
        char for char in value
        if unicodedata.category(char) not in {"So", "Sk"}
        and char not in {"\u200d", "\ufe0f", "\ufe0e"}
    ).strip()


def clean_markdown(value):
    value = re.sub(r"\[\[([^\]]+)\]\]\(([^)]*)\)", r"\1", value)
    value = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_~]", "", value)
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"\s+", " ", remove_emoji(value))
    return value.strip(" \t|:;–—-")


def main_projects_lines(readme):
    lines = readme.split("\n")
    heading_index = None
    heading_level = 2
    for index, line in enumerate(lines):
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        heading_text = clean_markdown(match.group(2)).casefold()
        if re.search(r"\bmain\s+projects?\b", heading_text):
            heading_index = index
            heading_level = len(match.group(1))
            break

    if heading_index is None:
        raise ValueError("Could not find the Main Projects section in the profile README.")

    section_lines = []
    for line in lines[heading_index + 1:]:
        match = re.match(r"^\s{0,3}(#{1,6})\s+", line)
        if match and len(match.group(1)) <= heading_level:
            break
        section_lines.append(line)
    return section_lines


def parse_projects(readme):
    projects = []
    seen = set()
    lines = main_projects_lines(readme)
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.strip()
        if not line or line.startswith(("![", "<", "|---", "---")):
            index += 1
            continue
        bullet = re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)(.+)$", line)
        if not bullet:
            index += 1
            continue

        item_line = bullet.group(1)
        bold_name = re.search(r"\*\*(.+?)\*\*", item_line)
        repo_link = re.search(r"\[\[\s*repo\s*\]\]\((https?://[^)]+)\)", item_line, flags=re.IGNORECASE)
        blog_link = re.search(r"\[\[\s*blog\s*\]\]\((https?://[^)]+)\)", item_line, flags=re.IGNORECASE)
        links = list(re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", item_line))
        github_link = next((link for link in links if "github.com" in link.group(2).lower()), None)
        github_url = repo_link.group(1).rstrip(".,)") if repo_link else github_link.group(2).rstrip(".,)") if github_link else ""
        if blog_link:
            blog_url = blog_link.group(1).rstrip(".,)")
        else:
            blog = next(
                (link for link in links if re.search(r"blog|article|post", link.group(1), re.IGNORECASE)
                 or re.search(r"blog|substack|medium\.com|dev\.to", link.group(2), re.IGNORECASE)),
                None,
            )
            blog_url = blog.group(2).rstrip(".,)") if blog else ""

        if bold_name:
            name = clean_markdown(bold_name.group(1))
        elif links:
            name = clean_markdown(links[0].group(1))
        else:
            name = clean_markdown(re.split(r"https?://|\s(?:[-–—:|])\s", item_line, maxsplit=1)[0])

        inline = re.sub(r"\[\[([^\]]+)\]\]\(([^)]+)\)", "", item_line)
        inline = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", "", inline)
        inline = re.sub(r"\*\*(.+?)\*\*", r"\1", inline)
        description = clean_markdown(inline)
        if description.casefold() == name.casefold():
            description = ""

        next_index = index + 1
        following_description = []
        while next_index < len(lines):
            continuation = lines[next_index]
            if not continuation.strip():
                if following_description:
                    break
                next_index += 1
                continue
            if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|#{1,6}\s+)", continuation):
                break
            following_description.append(continuation.strip())
            next_index += 1
        if not description and following_description:
            description = clean_markdown(" ".join(following_description))

        if not name or not github_url or github_url in seen:
            index = max(index + 1, next_index)
            continue
        seen.add(github_url)
        projects.append((name, description, github_url, blog_url))
        index = max(index + 1, next_index)
    return projects


def render_projects(projects):
    if not projects:
        return '<li class="collection-empty">No projects found in the Main Projects section.</li>'

    rows = []
    for name, description, github_url, blog_url in projects:
        blog_button = (
            '<a class="code-project-button" href="{}" target="_blank" rel="noopener noreferrer">Blog</a>'.format(
                html.escape(blog_url, quote=True)
            )
            if blog_url else ""
        )
        rows.append(
            '<li class="collection-entry"><div class="code-project-info">'
            '<span class="collection-title">{name}</span>{description}</div>'
            '<div class="code-project-actions"><a class="code-project-button" href="{github_url}" target="_blank" rel="noopener noreferrer">GitHub</a>{blog_button}</div></li>'.format(
                github_url=html.escape(github_url, quote=True),
                name=html.escape(name),
                blog_button=blog_button,
                description=(
                    '<span class="code-project-description">{}</span>'.format(html.escape(description))
                    if description else ""
                ),
            )
        )
    return "\n      ".join(rows)


def fill_code():
    response = requests.get(README_URL, timeout=30, headers={"User-Agent": "LaCavernaSite/1.0"})
    response.raise_for_status()
    projects = parse_projects(response.text)
    source = CODE_PAGE.read_text(encoding="utf-8")
    pattern = re.compile(f"{re.escape(START)}.*?{re.escape(END)}", flags=re.DOTALL)
    if not pattern.search(source):
        raise RuntimeError(f"Project placeholder not found in {CODE_PAGE}.")
    output = pattern.sub(
        lambda _: f"{START}\n      {render_projects(projects)}\n      {END}",
        source,
        count=1,
    )
    atomic_write_text(CODE_PAGE, output)
    logging.info("Updated Código with %s GitHub projects", len(projects))


if __name__ == "__main__":
    fill_code()
