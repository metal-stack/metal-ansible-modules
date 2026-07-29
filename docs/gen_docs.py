#!/usr/bin/env python3
import json
import os
import re
import sys

from ansible.utils.plugin_docs import get_docstring
from jinja2 import Environment, FileSystemLoader

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY = os.path.join(BASE, "library")
LOOKUP_PLUGINS = os.path.join(BASE, "lookup_plugins")
INVENTORY = os.path.join(BASE, "inventory")
DOCS = os.path.join(BASE, "docs")

RST_RE = re.compile(r"\b([CIBMUL]|HORIZONTALLINE)\(([^)]*)\)")


def rst_to_md(text):
    def _replace(m):
        tag, content = m.group(1), m.group(2)
        if tag == "C":
            return f"`{content}`"
        elif tag == "I":
            return f"*{content}*"
        elif tag == "B":
            return f"**{content}**"
        elif tag == "U":
            return f"<u>{content}</u>"
        elif tag == "M":
            return f"`{content}`"
        elif tag == "L":
            parts = content.split(",", 1)
            if len(parts) == 2:
                label, url = parts
                return f"[{label}]({url})"
            return f"`{content}`"
        elif tag == "HORIZONTALLINE":
            return "---"
        else:
            return content

    text = RST_RE.sub(_replace, text)
    text = text.replace("``", "`")
    return text


def fmt_default(val):
    if val is None:
        return ""
    if val is True:
        return "`true`"
    if val is False:
        return "`false`"
    if isinstance(val, str):
        return f"`{val}`"
    return f"`{val}`"


def fmt_choices(choices):
    if not choices:
        return ""
    return ", ".join(f"`{c}`" for c in choices)


def fmt_sample(val):
    if val is None:
        return "", False
    if isinstance(val, (dict, list)):
        return json.dumps(val, indent=2), True
    return str(val), False


def collect_params(options):
    params = []
    for name in sorted(options):
        opt = options[name]
        params.append(
            {
                "name": name,
                "description": rst_to_md(" ".join(opt.get("description", []))),
                "required": opt.get("required", False),
                "default": fmt_default(opt.get("default")),
                "choices": fmt_choices(opt.get("choices", [])),
                "type": opt.get("type") or "str",
            }
        )
    return params


def sample_anchor(ref):
    return f"sample-{ref}"


def collect_returns(returns):
    rets = []
    multi_samples = []
    for name in sorted(returns):
        ret = returns[name]
        sample_raw, is_multi = fmt_sample(ret.get("sample"))
        if is_multi:
            ref = f"sample_{name}"
            anchor = sample_anchor(ref)
            sample_escaped = f"[{ref}](#{anchor})"
            multi_samples.append((ref, sample_raw))
        else:
            sample_escaped = sample_raw.replace("|", "\\|").replace("\n", " ")
        rets.append(
            {
                "name": name,
                "description": rst_to_md(" ".join(ret.get("description", []))),
                "returned": ret.get("returned", ""),
                "type": ret.get("type", ""),
                "sample": sample_escaped,
            }
        )
    return rets, multi_samples


def main():
    module_names = sorted(
        f.replace(".py", "")
        for f in os.listdir(LIBRARY)
        if f.endswith(".py") and f != "__init__.py"
    )

    if not module_names:
        print("No modules found in library/", file=sys.stderr)
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(DOCS),
        keep_trailing_newline=False,
    )
    template = env.get_template("module.md.j2")

    os.makedirs(DOCS, exist_ok=True)

    for module_name in module_names:
        source_path = os.path.join(LIBRARY, f"{module_name}.py")
        doc, examples, returndocs, metadata = get_docstring(
            source_path, fragment_loader=None, is_module=True
        )
        if not doc:
            print(f"Warning: could not parse {source_path}", file=sys.stderr)
            continue

        options = collect_params(doc.get("options", {}))
        returns, multi_samples = collect_returns(returndocs or {})

        markdown = template.render(
            module_name=doc.get("module", "unknown"),
            short_description=rst_to_md(doc.get("short_description", "")),
            description=[rst_to_md(d) for d in doc.get("description", [])],
            options=options,
            returns=returns,
            multi_samples=multi_samples,
            examples=(examples or "").strip(),
            authors=doc.get("author", []),
            version_added=doc.get("version_added", ""),
            requirements=[rst_to_md(r) for r in doc.get("requirements", [])],
            status=", ".join(metadata.get("status", [])),
            supported_by=metadata.get("supported_by", ""),
        )

        out_path = os.path.join(DOCS, f"{module_name}.md")
        with open(out_path, "w") as f:
            f.write(markdown)

        print(f"Generated {out_path}")

    lookup_plugins = sorted(
        f.replace(".py", "")
        for f in os.listdir(LOOKUP_PLUGINS)
        if f.endswith(".py") and f != "__init__.py"
    )

    for plugin_name in lookup_plugins:
        source_path = os.path.join(LOOKUP_PLUGINS, f"{plugin_name}.py")
        doc, examples, returndocs, metadata = get_docstring(
            source_path, fragment_loader=None, is_module=False
        )
        if not doc:
            print(f"Warning: could not parse {source_path}", file=sys.stderr)
            continue

        options = collect_params(doc.get("options", {}))
        returns, multi_samples = collect_returns(returndocs or {})

        markdown = template.render(
            module_name=doc.get("lookup", "unknown"),
            short_description=rst_to_md(doc.get("short_description", "")),
            description=[rst_to_md(d) for d in doc.get("description", [])],
            options=options,
            returns=returns,
            multi_samples=multi_samples,
            examples=(examples or "").strip(),
            authors=doc.get("author", []),
            version_added=doc.get("version_added", ""),
            requirements=[rst_to_md(r) for r in doc.get("requirements", [])],
            status=", ".join(metadata.get("status", [])),
            supported_by=metadata.get("supported_by", ""),
        )

        out_path = os.path.join(DOCS, f"lookup_{plugin_name}.md")
        with open(out_path, "w") as f:
            f.write(markdown)

        print(f"Generated {out_path}")

    inventory_scripts = sorted(
        f.replace(".py", "")
        for f in os.listdir(INVENTORY)
        if f.endswith(".py") and f != "__init__.py"
    )

    for script_name in inventory_scripts:
        source_path = os.path.join(INVENTORY, f"{script_name}.py")
        doc, examples, returndocs, metadata = get_docstring(
            source_path, fragment_loader=None, is_module=False
        )
        if not doc:
            print(f"Warning: could not parse {source_path}", file=sys.stderr)
            continue

        options = collect_params(doc.get("options", {}))
        returns, multi_samples = collect_returns(returndocs or {})

        markdown = template.render(
            module_name=doc.get("inventory", "unknown"),
            short_description=rst_to_md(doc.get("short_description", "")),
            description=[rst_to_md(d) for d in doc.get("description", [])],
            options=options,
            returns=returns,
            multi_samples=multi_samples,
            examples=(examples or "").strip(),
            authors=doc.get("author", []),
            version_added=doc.get("version_added", ""),
            requirements=[rst_to_md(r) for r in doc.get("requirements", [])],
            status=", ".join(metadata.get("status", [])),
            supported_by=metadata.get("supported_by", ""),
        )

        out_path = os.path.join(DOCS, f"inventory_{script_name}.md")
        with open(out_path, "w") as f:
            f.write(markdown)

        print(f"Generated {out_path}")

    total = len(module_names) + len(lookup_plugins) + len(inventory_scripts)
    print(f"\nDone. {total} docs generated.")


if __name__ == "__main__":
    main()
