# coding=utf-8
from __future__ import unicode_literals

import csv
import re
from builtins import str
from io import IOBase
from pathlib import Path

import six
import yaml
from deprecation import deprecated
from snips_nlu_ontology import get_all_builtin_entities

from snips_nlu.__about__ import __version__
from snips_nlu.constants import (
    AUTOMATICALLY_EXTENSIBLE, DATA, MATCHING_STRICTNESS, SYNONYMS,
    USE_SYNONYMS, VALUE)
from snips_nlu.exceptions import EntityFormatError

AUTO_EXT_REGEX = re.compile(r'^#\sautomatically_extensible=(true|false)\s*$')


class Entity(object):
    """Entity data of a :class:`.Dataset`

    This class can represents both a custom or a builtin entity. When the
    entity is a builtin one, only the `name` attribute is relevant.

    Attributes:
        name (str): name of the entity
        utterances (list of :class:`.EntityUtterance`): entity utterances
            (only for custom entities)
        automatically_extensible (bool): whether or not the entity can be
            extended to values not present in the data (only for custom
            entities)
        use_synonyms (bool): whether or not to map entity values using
            synonyms (only for custom entities)
        matching_strictness (float): controls the matching strictness of the
            entity (only for custom entities). Must be between 0.0 and 1.0.
    """

    def __init__(self, name, utterances=None, automatically_extensible=True,
                 use_synonyms=True, matching_strictness=1.0):
        if utterances is None:
            utterances = []
        self.name = name
        self.utterances = utterances
        self.automatically_extensible = automatically_extensible
        self.use_synonyms = use_synonyms
        self.matching_strictness = matching_strictness

    @property
    def is_builtin(self):
        return self.name in get_all_builtin_entities()

    @classmethod
    def from_yaml(cls, yaml_dict):
        """Build an :class:`.Entity` from its YAML definition object

        Args:
            yaml_dict (dict or :class:`.IOBase`): object containing the YAML
                definition of the entity. It can be either a stream, or the
                corresponding python dict.

        Examples:
            An entity can be defined with a YAML document following the schema
            illustrated in the example below:

            >>> import io
            >>> import json
            >>> entity_yaml = io.StringIO('''
            ... # City Entity
            ... ---
            ... type: entity
            ... name: city
            ... automatically_extensible: false # default value is true
            ... use_synonyms: false # default value is true
            ... matching_strictness: 0.8 # default value is 1.0
            ... values:
            ...   - london
            ...   - [new york, big apple]
            ...   - [paris, city of lights]''')
            >>> entity = Entity.from_yaml(entity_yaml)
            >>> print(json.dumps(entity.json, indent=4, sort_keys=True))
            {
                "automatically_extensible": false,
                "data": [
                    {
                        "synonyms": [],
                        "value": "london"
                    },
                    {
                        "synonyms": [
                            "big apple"
                        ],
                        "value": "new york"
                    },
                    {
                        "synonyms": [
                            "city of lights"
                        ],
                        "value": "paris"
                    }
                ],
                "matching_strictness": 0.8,
                "use_synonyms": false
            }

        Raises:
            EntityFormatError: When the YAML dict does not correspond to the
                :ref:`expected entity format <yaml_entity_format>`
        """
        if isinstance(yaml_dict, IOBase):
            yaml_dict = yaml.safe_load(yaml_dict)

        object_type = yaml_dict.get("type")
        if object_type and object_type != "entity":
            raise EntityFormatError("Wrong type: '%s'" % object_type)
        entity_name = yaml_dict.get("name")
        if not entity_name:
            raise EntityFormatError("Missing 'name' attribute")
        auto_extensible = yaml_dict.get(AUTOMATICALLY_EXTENSIBLE, True)
        use_synonyms = yaml_dict.get(USE_SYNONYMS, True)
        matching_strictness = yaml_dict.get("matching_strictness", 1.0)
        utterances = []
        for entity_value in yaml_dict.get("values", []):
            if isinstance(entity_value, list):
                utterance = EntityUtterance(entity_value[0], entity_value[1:])
            elif isinstance(entity_value, str):
                utterance = EntityUtterance(entity_value)
            else:
                raise EntityFormatError(
                    "YAML entity values must be either strings or lists, but "
                    "found: %s" % type(entity_value))
            utterances.append(utterance)

        return cls(name=entity_name,
                   utterances=utterances,
                   automatically_extensible=auto_extensible,
                   use_synonyms=use_synonyms,
                   matching_strictness=matching_strictness)

    @classmethod
    @deprecated(deprecated_in="0.18.0", removed_in="0.19.0",
                current_version=__version__, details="Use from_yaml instead")
    def from_file(cls, filepath):
        """Build an :class:`.Entity` from a text file"""
        filepath = Path(filepath)
        stem = filepath.stem
        if not stem.startswith("entity_"):
            raise EntityFormatError(
                "Entity filename should start with 'entity_' but found: %s"
                % stem)
        entity_name = stem[7:]
        if not entity_name:
            raise EntityFormatError("Entity name must not be empty")
        utterances = []
        with filepath.open(encoding="utf-8") as f:
            it = f
            if six.PY2:
                it = list(utf_8_encoder(it))
            reader = csv.reader(list(it))
            autoextent = True
            for row in reader:
                if not row or not row[0].strip():
                    continue
                if six.PY2:
                    row = [cell.decode("utf-8") for cell in row]
                value = row[0]
                if reader.line_num == 1:
                    m = AUTO_EXT_REGEX.match(row[0])
                    if m:
                        autoextent = not m.group(1).lower() == 'false'
                        continue
                if len(row) > 1:
                    synonyms = row[1:]
                else:
                    synonyms = []
                utterances.append(EntityUtterance(value, synonyms))
        return cls(entity_name, utterances,
                   automatically_extensible=autoextent, use_synonyms=True)

    @property
    def json(self):
        """Returns the entity in json format"""
        if self.is_builtin:
            return dict()
        return {
            AUTOMATICALLY_EXTENSIBLE: self.automatically_extensible,
            USE_SYNONYMS: self.use_synonyms,
            DATA: [u.json for u in self.utterances],
            MATCHING_STRICTNESS: self.matching_strictness
        }


class EntityUtterance(object):
    """Represents a value of a :class:`.CustomEntity` with potential synonyms

    Attributes:
        value (str): entity value
        synonyms (list of str): The values to remap to the utterance value
        """

    def __init__(self, value, synonyms=None):
        self.value = value
        if synonyms is None:
            synonyms = []
        self.synonyms = synonyms

    @property
    def variations(self):
        return [self.value] + self.synonyms

    @property
    def json(self):
        return {VALUE: self.value, SYNONYMS: self.synonyms}


def utf_8_encoder(f):
    for line in f:
        yield line.encode("utf-8")
