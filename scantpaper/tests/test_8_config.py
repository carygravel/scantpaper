"test config helper functions"

import os
from types import SimpleNamespace
from config import (
    read_config,
    write_config,
    add_defaults,
    remove_invalid_paper,
    DEFAULTS,
)
from basedocument import slurp


def test_config():
    "test config helper functions"
    rc = "test"

    #########################

    config = """{
    "version": "1.3.3"
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)
    example = {"version": "1.3.3"}
    output = read_config(rc)
    assert output == example, "Read JSON"

    #########################

    write_config(rc, example)

    example = config.split("\n")
    output = slurp(rc).split("\n")

    assert output == example, "Write JSON"

    #########################

    output = {"version": "1.3.3"}
    output["non-existant-option"] = None
    add_defaults(output)
    example = DEFAULTS.copy()
    example["version"] = "1.3.3"
    assert output == example, "add_defaults"

    #########################

    output = {"Paper": {1: ["stuff"]}}
    remove_invalid_paper(output["Paper"])
    example = {"Paper": {}}
    assert output == example, "remove_invalid_paper (contents)"

    #########################

    output = {
        "Paper": {
            "<>": {
                "x": 210,
                "y": 297,
                "l": 0,
                "t": 0,
            }
        }
    }
    remove_invalid_paper(output["Paper"])
    example = {"Paper": {}}
    assert output == example, "remove_invalid_paper (name)"

    #########################

    config = """{
   "user_defined_tools" : "gimp %i"
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    example = {"user_defined_tools": ["gimp %i"]}
    output = read_config(rc)

    assert output == example, "force user_defined_tools to be an array"

    #########################

    config = """{
   "profile" : {
      "crash" : null
   },
   "version" : "1.7.3"
}
"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    example = {"profile": {}, "version": "1.7.3"}
    output = read_config(rc)

    assert output == example, "remove undefined profiles"


def test_config2():
    "test config helper functions"
    rc = "test"

    #########################

    config = """{
    "device list": [
        {
            "label": "test_label",
            "model": "test_model",
            "name": "test_name",
            "vendor": "test_vendor"
        }
    ],
    "version": "1.7.3"
}"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    example = {
        "device list": [
            SimpleNamespace(
                name="test_name",
                vendor="test_vendor",
                model="test_model",
                label="test_label",
            )
        ],
        "version": "1.7.3",
    }
    output = read_config(rc)

    assert output == example, "Deserialise device list"

    #########################

    write_config(rc, example)
    output = slurp(rc)
    assert output == config, "Serialise device list"

    #########################

    config = """{
   "version" : "
}
"""
    with open(rc, "w", encoding="utf-8") as fh:
        fh.write(config)

    output = read_config(rc)

    assert output == {}, "deal with corrupt config"

    #########################

    os.remove(f"{rc}.old")  # rc doesn't exist because it was corrupt
