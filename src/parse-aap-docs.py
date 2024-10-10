import re
from pathlib import Path


AAP_DOCS = "/home/ttakamiy/git/ansible/aap-docs"

class ParseAdocs:

    def __init__(self, base_dir):
        self.base_dir = base_dir

    def run(self):
        self.adocs_dict = self.get_dict()
        self.parse_attributes()
        self.parse_include()

    def get_adocs(self):
        return list(
            filter(lambda x: "/archive/" not in str(x), Path(self.base_dir).joinpath("downstream").rglob("*.adoc")))

    def get_dict(self):
        d = {}
        for adoc in self.get_adocs():
            path_name = str(adoc)
            i = path_name.find("/downstream/")
            project_file_name = path_name[i:]
            d[project_file_name] = { "path_name": path_name }
        return d


    def find_include_file(self, source, include_file):
        file_name = f"/downstream/{include_file}"
        found = file_name in self.adocs_dict

        if not found:
            if include_file.startswith("../"):
                file_name = f"/downstream/{include_file[3:]}"
                found = file_name in self.adocs_dict

        if not found:
            i = source.rfind("/")
            if include_file.startswith("../"):
                i = source[:i].rfind("/")
                file_name = f"{source[:i]}/{include_file[3:]}"
            else:
                file_name = f"{source[:i]}/{include_file}"
            found = file_name in self.adocs_dict

        if not found:
            for subdirectory in ["assemblies", "modules"]:
                file_name = f"/downstream/{subdirectory}/{include_file}"
                found = file_name in self.adocs_dict
                if found:
                    break

        if not found:
            print(f"NOT FOUND: {include_file} (source: {source})")

        return found


    def parse_include(self):
        not_found = 0
        include_pattern = re.compile(r"^\s*include::([\w\./\-_]+).*$")
        for k,v in self.adocs_dict.items():
            # print(f"SOURCE: {k}")
            for line in open(v["path_name"]):
                m = include_pattern.match(line)
                if m:
                    include_file = m.group(1)
                    include_file = self.substitude_attributes(include_file)
                    # print(f"include_file={include_file}")
                    found = self.find_include_file(k, include_file)
                    if not found:
                        not_found += 1
        print(f"NOT FOUND: {not_found}")

    def substitude_attributes(self, line):
        pattern = re.compile(r"{(\w+)}")
        attributes = pattern.findall(line)
        for attribute in attributes:
            if attribute in self.attributes_dict:
                line = line.replace(f"{{{attribute}}}", f"{self.attributes_dict[attribute]}")
            else:
                print(f"Attribute {attribute} is not found.")
        return line

    def parse_attributes(self):
        self.attributes_dict = {}
        pattern = re.compile(r":(\w+):\s*(.+)$")
        menu_pattern = re.compile(r"^menu:([\w ]+)\[([\w >]+)\]$")
        attributes_adoc = Path(self.base_dir).joinpath("downstream").joinpath("attributes").joinpath("attributes.adoc")
        for line in open(attributes_adoc):
            line = line.strip()
            if len(line) == 0 or line.startswith("//"):
                continue
            m = pattern.match(line)
            if m:
                key = m.group(1)
                value = self.substitude_attributes(m.group(2))
                m = menu_pattern.match(value)
                if m:
                    value = f"{m.group(1)} > {m.group(2)}"
                # print(key, value)
                self.attributes_dict[key] = value


def main():
    ParseAdocs(AAP_DOCS).run()

if __name__ == "__main__":
    main()