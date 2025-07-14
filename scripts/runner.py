from scripts.generate_desk_html import generate_desk_html
from scripts.generate_doc_html import generate_doc_html
from scripts.generate_doc_imgs import generate_doc_imgs
from scripts.get_substack_posts import get_substack_posts


if __name__=="__main__":
    get_substack_posts()
    generate_doc_html()
    generate_desk_html()
    generate_doc_imgs()