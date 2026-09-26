get_substack_posts --> fill_embeddings
get_substack_posts --> get_doc_images
fill_embeddings --> generate_docs
get_doc_images --> generate_docs
generate_docs --> fill_index

fill_sections (books, movies, music, quotes)
fill_code (Código, called by runner.py and the weekly GitHub Action)
