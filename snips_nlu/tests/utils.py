from __future__ import unicode_literals

import json
import shutil
import tempfile
import traceback as tb
from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase

from snips_nlu_ontology import get_all_languages

from snips_nlu.intent_parser import IntentParser
from snips_nlu.pipeline.configs import ProcessingUnitConfig
from snips_nlu.resources import load_resources
from snips_nlu.result import empty_result
from snips_nlu.utils import json_string, unicode_string

TEST_PATH = Path(__file__).parent
TEST_RESOURCES_PATH = TEST_PATH / "resources"
SAMPLE_DATASET_PATH = TEST_RESOURCES_PATH / "sample_dataset.json"
BEVERAGE_DATASET_PATH = TEST_RESOURCES_PATH / "beverage_dataset.json"
WEATHER_DATASET_PATH = TEST_RESOURCES_PATH / "weather_dataset.json"
PERFORMANCE_DATASET_PATH = TEST_RESOURCES_PATH / "performance_dataset.json"


# pylint: disable=invalid-name
class SnipsTest(TestCase):

    def setUp(self):
        for l in get_all_languages():
            load_resources(l)

    @contextmanager
    def fail_if_exception(self, msg):
        try:
            yield
        except Exception:  # pylint: disable=W0703
            trace = tb.format_exc()
            self.fail("{}\b{}".format(msg, trace))

    def assertJsonContent(self, json_path, expected_dict):
        if not json_path.exists():
            self.fail("Json file not found: %s" % str(json_path))
        with json_path.open(encoding="utf8") as f:
            data = json.load(f)
        self.assertDictEqual(expected_dict, data)

    def assertFileContent(self, path, expected_content):
        if not path.exists():
            self.fail("File not found: %s" % str(path))
        with path.open(encoding="utf8") as f:
            data = f.read()
        self.assertEqual(expected_content, data)

    @staticmethod
    def writeJsonContent(path, json_dict):
        json_content = json_string(json_dict)
        with path.open(mode="w") as f:
            f.write(json_content)

    @staticmethod
    def writeFileContent(path, content):
        with path.open(mode="w") as f:
            f.write(unicode_string(content))


class FixtureTest(SnipsTest):
    # pylint: disable=protected-access
    def setUp(self):
        super(FixtureTest, self).setUp()
        self.fixture_dir = Path(tempfile.mkdtemp())
        if not self.fixture_dir.exists():
            self.fixture_dir.mkdir()

        self.tmp_file_path = self.fixture_dir / next(
            tempfile._get_candidate_names())
        while self.tmp_file_path.exists():
            self.tmp_file_path = self.fixture_dir / next(
                tempfile._get_candidate_names())

    def tearDown(self):
        if self.fixture_dir.exists():
            shutil.rmtree(str(self.fixture_dir))


def get_empty_dataset(language):
    return {
        "intents": {},
        "entities": {},
        "language": language,
    }


with SAMPLE_DATASET_PATH.open(encoding='utf8') as dataset_file:
    SAMPLE_DATASET = json.load(dataset_file)

with BEVERAGE_DATASET_PATH.open(encoding='utf8') as dataset_file:
    BEVERAGE_DATASET = json.load(dataset_file)

with WEATHER_DATASET_PATH.open(encoding='utf8') as dataset_file:
    WEATHER_DATASET = json.load(dataset_file)

with PERFORMANCE_DATASET_PATH.open(encoding='utf8') as dataset_file:
    PERFORMANCE_DATASET = json.load(dataset_file)


class MockIntentParserConfig(ProcessingUnitConfig):
    unit_name = "mock_intent_parser"

    def to_dict(self):
        return {"unit_name": self.unit_name}

    @classmethod
    def from_dict(cls, obj_dict):
        return cls()


class MockIntentParser(IntentParser):
    unit_name = "mock_intent_parser"
    config_type = MockIntentParserConfig

    def fit(self, dataset, force_retrain):
        self._fitted = True
        return self

    @property
    def fitted(self):
        return hasattr(self, '_fitted') and self._fitted

    def parse(self, text, intents, top_n):
        return empty_result(text)

    def get_intents(self, text):
        return []

    def get_slots(self, text, intent):
        return []

    def persist(self, path):
        path = Path(path)
        path.mkdir()
        with (path / "metadata.json").open(mode="w") as f:
            f.write(json_string({"unit_name": self.unit_name}))

    @classmethod
    def from_path(cls, path, **shared):
        cfg = cls.config_type()
        return cls(cfg)
