import copy
import os
import re
import sys
from pathlib import Path

import requests


class ParseAAPDocs:
    """
    Parse the aap-docs repository and locate Red Hat product document URLs for each
    source Asciidoc files so that they can be used as referenced document links
    displayed on the chatbot UI.
    """

    def __init__(self, base_dir, project_document_path, files_to_skip, do_validate=False):
        self.base_dir = base_dir
        self.project_document_path = project_document_path
        self.files_to_skip = files_to_skip
        self.do_validate = do_validate

    def run(self):
        self.parse_attributes()
        self.adocs_dict = self.get_dict()
        self.parse_doc_info_files()
        self.parse_include()
        self.parse_title_docs()

        has_url = list(filter(lambda x: self.adocs_dict[x]["url"] is not None, self.adocs_dict))
        print(f"has_url: {len(has_url)}")
        print(f"total: {len(self.adocs_dict)}")

    def validate(self, adoc):
        url = adoc["url"]
        try:
            response = requests.get(url, allow_redirects=False)
            if response.status_code == 200:
                return True
            else:
                print(f"INVALID: {url} status_code={response.status_code}")
                return False
        except requests.ConnectionError as exception:
            print(f"INVALID: {url} ConnectionError")
            return False

    def parse_title_docs(self):
        title_docs = list(filter(lambda x: self.adocs_dict[x]["url"] != None, self.adocs_dict))
        for title_doc in title_docs:
            if title_doc in self.files_to_skip:
                self.adocs_dict[title_doc]["url"] = None
                continue
            self.adocs_dict[title_doc]["url"] = self.adocs_dict[title_doc]["url"].replace(
                "/html/", "/html-single/"
            )
            print(title_doc, self.adocs_dict[title_doc]["url"])

            context = {
                "name": None,
                "url": self.adocs_dict[title_doc]["url"],
                "base_url": self.adocs_dict[title_doc]["url"],
            }
            self.adocs_dict[title_doc]["url"] = self.adocs_dict[title_doc]["url"] + "/index"
            self.simulate_includes(self.adocs_dict[title_doc], context)

    def simulate_includes(self, adoc, context):
        id = None
        nested_assembly = adoc["nested_assembly"]
        context_save = copy.copy(context) if nested_assembly else None

        if adoc["id"]:
            id = adoc["id"]
            if "{context}" in id:
                if context["name"] is None:
                    id = id.replace("_{context}", "")
                else:
                    id = id.replace("{context}", context["name"])
            if adoc["url"]:
                print(f"A URL is already set for {adoc['project_file_name']}")
            else:
                if context["name"]:
                    if context["url"] == context["base_url"]:
                        adoc["url"] = f"{context['url']}/index#{id}"
                    else:
                        adoc["url"] = f"{context['url']}#{id}"
                else:
                    adoc["url"] = f"{context['url']}/{id}"
                if self.do_validate and not self.validate(adoc):
                    sys.exit(1)
                print(
                    f"A URL {adoc['url']} is set for {adoc['project_file_name']} context={context}"
                )

        if adoc["context"]:
            if not context["name"] and id:
                context["url"] = f"{context['url']}/{id}"
            context["name"] = adoc["context"]

        for include in adoc["includes"]:
            self.simulate_includes(self.adocs_dict[include], context)

        if context_save:
            context["name"] = context_save["name"]
            context["url"] = context_save["url"]

    def get_adocs(self):
        return list(
            filter(
                lambda x: "/archive/" not in str(x),
                Path(self.base_dir).joinpath(self.project_document_path).rglob("*.adoc"),
            )
        )

    def parse_doc_info_files(self):
        count = 0
        title_pattern = re.compile(r"^\s*<title>(.+)</title>\s*$")
        docinfo_files = list(
            filter(
                lambda x: "/archive/" not in str(x),
                Path(self.base_dir).joinpath(self.project_document_path).rglob("docinfo.xml"),
            )
        )
        for docinfo in docinfo_files:
            for line in open(docinfo):
                m = title_pattern.match(line)
                if m:
                    title = m.group(1).strip()
                    if title in self.title_dict:
                        dir_name = str(docinfo.parents[0])
                        i = dir_name.index(f"{self.project_document_path}/")
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

    def parse_adoc(self, adoc_path):
        id = None
        id_pattern = re.compile(r'\[id=["\']([^"\']+)["\']\]')
        context = None
        context_pattern = re.compile(r":context:\s*(.+)")
        content_type = None
        content_type_pattern = re.compile(r":_mod-docs-content-type:\s*(.+)")
        nested_assembly = False
        nested_assembly_pattern = re.compile(r"ifdef::parent.+\[:context: {parent-context}\]")
        for line in open(adoc_path):
            line = line.strip()
            m = id_pattern.match(line)
            if m:
                id = m.group(1)
            m = context_pattern.match(line)
            if m:
                context = m.group(1)
            m = content_type_pattern.match(line)
            if m:
                content_type = m.group(1)
            m = nested_assembly_pattern.match(line)
            if m:
                nested_assembly = True

        return id, context, content_type, nested_assembly

    def get_dict(self):
        d = {}
        for adoc in self.get_adocs():
            path_name = str(adoc)
            i = path_name.find(f"{self.project_document_path}/")
            project_file_name = path_name[i:]
            id, context, content_type, nested_assembly = self.parse_adoc(path_name)
            d[project_file_name] = {
                "project_file_name": project_file_name,
                "path_name": path_name,
                "includes": [],
                "url": None,
                "id": id,
                "context": context,
                "content_type": content_type,
                "nested_assembly": nested_assembly,
            }
        return d

    def find_include_file(self, source, include_file):
        base_path = Path(self.base_dir)
        parent_path = base_path.joinpath(Path(source).parents[0])
        include_file_path = parent_path.joinpath(include_file)
        include_file_path = os.path.realpath(include_file_path)
        i = include_file_path.find(f"{self.project_document_path}/")
        file_name = include_file_path[i:]
        if file_name not in self.adocs_dict:
            print(f"NOT FOUND: {include_file} (source: {source})")
            file_name = None
        return file_name

    def parse_include(self):
        include_pattern = re.compile(r"^\s*include::([\w\./\-_]+).*$")
        for k, v in self.adocs_dict.items():
            for line in open(v["path_name"]):
                m = include_pattern.match(line)
                if m:
                    include_file = m.group(1)
                    include_file = self.substitude_attributes(include_file)
                    file_name = self.find_include_file(k, include_file)
                    if file_name:
                        v["includes"].append(file_name)

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
        attributes_adoc = (
            Path(self.base_dir)
            .joinpath(self.project_document_path)
            .joinpath("attributes")
            .joinpath("attributes.adoc")
        )
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
                    self.title_dict[value] = key[len("Title") :]


def main():
    base_dir = "/home/ttakamiy/git/ansible/aap-docs"
    project_document_path = "downstream"
    files_to_skip = [
        "downstream/titles/aap-hardening/master.adoc",
        "downstream/titles/upgrade/master.adoc",
        "downstream/titles/playbooks/playbooks-reference/master.adoc",
    ]
    ParseAAPDocs(base_dir, project_document_path, files_to_skip, do_validate=True).run()


if __name__ == "__main__":
    main()
