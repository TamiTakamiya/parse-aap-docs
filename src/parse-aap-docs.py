import os
import re
from pathlib import Path


class ParseAdocs:

    def __init__(self, base_dir):
        self.base_dir = base_dir


    def run(self):
        self.parse_attributes()
        self.adocs_dict = self.get_dict()
        self.parse_doc_info_files()
        self.parse_include()

        # for k,v in self.adocs_dict.items():
        #     print(v)


    def get_adocs(self):
        return list(
            filter(lambda x: "/archive/" not in str(x), Path(self.base_dir).joinpath("downstream").rglob("*.adoc")))

    def parse_doc_info_files(self):
        count = 0
        title_pattern = re.compile(r"^\s*<title>(.+)</title>\s*$")
        docinfo_files = list(filter(lambda x: "/archive/" not in str(x), Path(self.base_dir).joinpath("downstream").rglob("docinfo.xml")))
        for docinfo in docinfo_files:
            for line in open(docinfo):
                m = title_pattern.match(line)
                if m:
                    title = m.group(1).strip()
                    if title in self.title_dict:
                        pass
                        # print(f"{title} -> {self.title_dict[title]}")
                        dir_name = str(docinfo.parents[0])
                        i = dir_name.index("downstream/")
                        master_adoc = f"{dir_name[i:]}/master.adoc"
                        if master_adoc not in self.adocs_dict:
                            print(f"NOT FOUND: {master_adoc}")
                        else:
                            url = self.attributes_dict["URL" + self.title_dict[title]]
                            self.adocs_dict[master_adoc]["url"] = url
                    else:
                        print(f"{title} IS NOT FOUND")
                    count += 1
        return

    def get_adoc_id_and_context(self, adoc_path):
        id = None
        id_pattern = re.compile(r'\[id=["\']([^"\']+)["\']\]')
        context = None
        context_pattern = re.compile(r':context:\s*(.+)')
        for line in open(adoc_path):
            line = line.strip()
            m = id_pattern.match(line)
            if m:
                id = m.group(1)
                if '{' in id:
                    print(f"id={id} {adoc_path}")
            m = context_pattern.match(line)
            if m:
                context = m.group(1)
                print(f"context={context}")

        return id,context


    def get_dict(self):
        d = {}
        for adoc in self.get_adocs():
            path_name = str(adoc)
            i = path_name.find("downstream/")
            project_file_name = path_name[i:]
            id, context = self.get_adoc_id_and_context(path_name)
            d[project_file_name] = {
                "path_name": path_name,
                "includes": set(),
                "included_by": set(),
                "broken_links": set(),
                "url": None,
                "id": id,
                "context": context,
            }
        return d


    def find_include_file(self, source, include_file):
        base_path = Path(self.base_dir)
        parent_path = base_path.joinpath(Path(source).parents[0])
        include_file_path = parent_path.joinpath(include_file)
        include_file_path = os.path.realpath(include_file_path)
        i = include_file_path.find("downstream/")
        file_name = include_file_path[i:]
        if file_name not in self.adocs_dict:
            print(f"NOT FOUND: {include_file} (source: {source})")
            file_name = None
        return file_name


    def parse_include(self):
        not_found = 0
        include_pattern = re.compile(r"^\s*include::([\w\./\-_]+).*$")
        for k,v in self.adocs_dict.items():
            for line in open(v["path_name"]):
                m = include_pattern.match(line)
                if m:
                    include_file = m.group(1)
                    include_file = self.substitude_attributes(include_file)
                    file_name = self.find_include_file(k, include_file)
                    if file_name is None:
                        not_found += 1
                        v["broken_links"].add(include_file)
                    else:
                        v["includes"].add(file_name)
                        if file_name in self.adocs_dict:
                            self.adocs_dict[file_name]["included_by"].add(k)
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
        self.title_dict = {}
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
                self.attributes_dict[key] = value
                if key.startswith("Title"):
                    self.title_dict[value] = key[len("Title"):]


def main():
    AAP_DOCS = "/home/ttakamiy/git/ansible/aap-docs"
    ParseAdocs(AAP_DOCS).run()

if __name__ == "__main__":
    main()