import logging
import json
import os
import glob

from scripts.utils import ROOT_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

path = f"{ROOT_DIR}/Documents"
logging.info(f"Documents path: {path}")

def write_code(text, template, file_path):
    logging.debug(f"Processing file for write_code: {file_path}")
    res = template.read()
    lines = [i.replace("\t", "&nbsp&nbsp") for i in text.readlines()]
    title = lines[0]
    body = "<br>".join([i.strip() for i in lines[1:]])

    if "\t" in body:
        logging.warning(f"Tabs found in content for {file_path}")

    posts_file = f"{ROOT_DIR}/posts.json"
    logging.debug(f"Loading posts from {posts_file}")
    with open(posts_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    relative_link = ".." + file_path.replace(ROOT_DIR, "")
    matches = [i for i in data if i["link"] == relative_link]
    if not matches:
        logging.error(f"No catalog entry found for {file_path}")
        return

    doc_data = matches[0]

    res = res.replace("{{title}}", title)
    res = res.replace("{{text}}", body)
    res = res.replace("{{img_link}}", doc_data["img_link"])
    res = res.replace("{{img_meta}}", doc_data["img_meta"])
    res = res.replace("{{author}}", "Sánchez")
    res = res.replace("{{tags}}", str(doc_data["tags"]).replace("'", ""))

    logging.info(f"Generated HTML for {file_path}")
    return res

def generate_doc_html():
    for filename in os.listdir(path):
        if filename.endswith(".html"):
            file_path = os.path.join(path, filename)
            os.remove(file_path)
            logging.info(f"Removed: {file_path}")

    template_path = f"{ROOT_DIR}/Sections/archive_template.html"
    for file in glob.glob(os.path.join(path, '*.txt')):
        logging.info(f"Converting {file}")
        with open(file, "r", encoding='utf-8') as f_origin, \
            open(template_path, "r", encoding='utf-8') as f_template:
            f_dest_path = f"{path}/{os.path.splitext(os.path.basename(file))[0]}.html"
            html_code = write_code(f_origin, f_template, f_dest_path)
            if html_code:
                with open(f_dest_path, "w", encoding='utf-8') as f_dest:
                    f_dest.write(html_code)
                    logging.info(f"Wrote: {f_dest_path}")

if __name__=="__main__":
    generate_doc_html()