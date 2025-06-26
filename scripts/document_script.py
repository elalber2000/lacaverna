import os, glob
 
path = r"C:\Users\ASUS\Desktop\Sanchez\Programas\LaCaverna\Documents"

def write_code(text, template):
    res = template.read()
    lines = [i.replace("\t","&nbsp&nbsp") for i in text.readlines()]
    title = lines[0]
    text = "<br>".join([i.strip() for i in lines[1:]])

    if("\t" in text):
        print(text)
    
    return res.replace("My title",title).replace("Lorem ipsum",text)


for filename in os.listdir(path):
    if filename.endswith(".html"):
        file_path = os.path.join(path, filename)
        os.remove(file_path)
        print(f"Removed: {file_path}")

for file in glob.glob(os.path.join(path, '*.txt')):
    print(f"Converting {file}")
    with open(file, "r", encoding='utf-8') as f_origin, open(r"C:\Users\ASUS\Desktop\Sanchez\Programas\LaCaverna\Sections\library_template.html","r", encoding='utf-8') as f_template:
        with open(path+"\\"+file.split("\\")[-1].split(".")[0]+".html", "w", encoding='utf-8') as f_dest:
            f_dest.write(write_code(f_origin, f_template))