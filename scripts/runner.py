from get_substack_posts import get_substack_posts
from fill_embeddings import fill_embeddings
from get_doc_images import get_doc_images
from generate_docs import generate_docs
from fill_index import fill_index
from fill_sections import fill_sections
from fill_code import fill_code
from utils import configure_logging

import logging


PIPELINE = (
    get_substack_posts,
    fill_embeddings,
    get_doc_images,
    generate_docs,
    fill_index,
    fill_sections,
    fill_code,
)


def main() -> None:
    configure_logging()
    for task in PIPELINE:
        logging.info("Running %s", task.__name__)
        task()


if __name__ == "__main__":
    main()
