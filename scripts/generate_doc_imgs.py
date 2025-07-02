import logging
from pathlib import Path
import requests
import random
import os
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import json

from scripts.utils import ROOT_DIR


PALETTE = {
    "dark": np.array([23,  23,  23]),
    "blue": np.array([155, 98,  78]),
    "lightblue": np.array([184, 117, 94]),
    "white": np.array([237, 232, 229]),
}

def apply_gradient_map(gray, gradient, thresholds):
    """
    gray       : 2D numpy array [0–255]
    gradient   : dict of BGR colors
    thresholds : list of three floats in (0,1) for bin edges
    """
    norm = gray.astype(np.float32) / 255.0
    edges = np.quantile(norm, thresholds)
    palette = np.stack([
        gradient["dark"],
        gradient["blue"],
        gradient["lightblue"],
        gradient["white"],
    ], axis=0)
    bins = np.digitize(norm, edges)
    bins = np.clip(bins, 0, palette.shape[0]-1)
    return palette[bins].astype(np.uint8)

def write_metadata(text):
    with open("metadata.txt", "a", encoding="utf-8") as f:
      f.write(text + "\n")
    return

def stylize_image_array(img_arr, thresholds=(0.25,0.5,0.75), blur_ksize=(5,5)):
    """
    img_arr    : BGR image
    thresholds : quantile thresholds for luminosity
    blur_ksize : tuple kernel size for Gaussian blur
    """
    gray = cv2.cvtColor(img_arr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, blur_ksize, 0)
    return apply_gradient_map(blurred, PALETTE, thresholds)

def fetch_random_met_image(min_val=400000, max_val=600000, randseed=None, title=None):
    for i in range(100):
        if randseed is None or i>0:
           obj_id = random.randint(min_val, max_val)
        else:
           obj_id = randseed
        url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
        print(url)
        res = requests.get(url)
        if res.status_code != 200:
            continue
        data = res.json()
        img_url = data.get("primaryImage")
        if img_url:
            print(f"Got object {obj_id}: {data.get('title')}")
            meta = {
                "id": data['objectID'],
                "title": data['title'],
                "artist": data['artistDisplayName'],
            }
            return img_url, meta
    raise Exception("No valid image found.")

def process_met_image(
    thresholds=(0.25,0.5,0.75),
    blur_ksize=(5,5),
    randseed=None,
    title=None,
  ):
    img_url, meta = fetch_random_met_image(randseed=randseed, title=title)
    img = Image.open(BytesIO(requests.get(img_url).content)).convert("RGB")
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    stylized = stylize_image_array(img_cv, thresholds, blur_ksize)
    print("Stylized image generated")
    return stylized, meta

def search_image(query):
    res = requests.get(f"https://collectionapi.metmuseum.org/public/collection/v1/search?q={query.lower().replace(' ', '_')}")
    if res.status_code != 200:
        print("Error cant fetch image")
        return None
    else:
        data = res.json()
        try:
            res = data["objectIDs"][0]
        except:
            res = None
    return res

if __name__=="__main__":
    posts_path = Path(ROOT_DIR) / "posts.json"
    logging.info(f"Loading existing posts from {posts_path}")
    if posts_path.exists() and posts_path.stat().st_size > 0:
        with open(posts_path, "r", encoding="utf-8") as f:
            posts = json.load(f)

    for i in posts:
        if i["img_link"] in os.listdir(f"{ROOT_DIR}/Images/Library"):
            continue
        img, meta = process_met_image(randseed=search_image(i["title"]), title=i["title"])
        cv2.imwrite(f"images/{i['img_link'].replace('../Images/Library/', '')}", img)