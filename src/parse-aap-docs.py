import re
from pathlib import Path


AAP_DOCS = "/home/ttakamiy/git/ansible/aap-docs"


def get_adocs(base_dir):
    return list(filter(lambda x: "/archive/" not in str(x), Path(base_dir).joinpath("downstream").rglob("*.adoc")))

def get_dict(adocs):
    d = {}
    for adoc in adocs:
        path_name = str(adoc)
        i = path_name.find("/downstream/")
        project_file_name = path_name[i:]
        d[project_file_name] = { "path_name": path_name }
    return d

def find_include_file(adocs_dict, source, include_file):
    found = False

    file_name = f"/downstream/{include_file}"
    found = file_name in adocs_dict

    if not found:
        if include_file.startswith("../"):
            file_name = f"/downstream/{include_file[3:]}"
            found = file_name in adocs_dict

    if not found:
        i = source.rfind("/")
        if include_file.startswith("../"):
            i = source[:i].rfind("/")
            file_name = f"{source[:i]}/{include_file[3:]}"
        else:
            file_name = f"{source[:i]}/{include_file}"
        found = file_name in adocs_dict

    if not found:
        for subdirectory in ["assemblies", "modules"]:
            file_name = f"/downstream/{subdirectory}/{include_file}"
            found = file_name in adocs_dict
            if found:
                break

    if not found:
        print(f"NOT FOUND: {include_file} (source: {source})")

    return found


def parse_include(adocs_dict, attributes_dict):
    not_found = 0
    include_pattern = re.compile(r"^\s*include::([\w\./\-_]+).*$")
    for k,v in adocs_dict.items():
        # print(f"SOURCE: {k}")
        for line in open(v["path_name"]):
            m = include_pattern.match(line)
            if m:
                include_file = m.group(1)
                include_file = substitude_attributes(attributes_dict, include_file)
                # print(f"include_file={include_file}")
                found = find_include_file(adocs_dict, k, include_file)
                if not found:
                    not_found += 1
    print(f"NOT FOUND: {not_found}")

def substitude_attributes(attributes_dict, line):
    pattern = re.compile(r"{(\w+)}")
    attributes = pattern.findall(line)
    for attribute in attributes:
        if attribute in attributes_dict:
            line = line.replace(f"{{{attribute}}}", f"{attributes_dict[attribute]}")
        else:
            print(f"Attribute {attribute} is not found.")
    return line

def parse_attributes(base_dir):
    attributes_dict = {}
    pattern = re.compile(r":(\w+):\s*(.+)$")
    menu_pattern = re.compile(r"^menu:([\w ]+)\[([\w >]+)\]$")
    attributes_adoc = Path(base_dir).joinpath("downstream").joinpath("attributes").joinpath("attributes.adoc")
    for line in open(attributes_adoc):
        line = line.strip()
        if len(line) == 0 or line.startswith("//"):
            continue
        m = pattern.match(line)
        if m:
            key = m.group(1)
            value = substitude_attributes(attributes_dict, m.group(2))
            m = menu_pattern.match(value)
            if m:
                value = f"{m.group(1)} > {m.group(2)}"
            # print(key, value)
            attributes_dict[key] = value
    return attributes_dict

def process(base_dir):
    adocs_dict = get_dict(get_adocs(base_dir))
    attributes_dict = parse_attributes(base_dir)
    parse_include(adocs_dict, attributes_dict)

def main():
    process(AAP_DOCS)

if __name__ == "__main__":
    main()