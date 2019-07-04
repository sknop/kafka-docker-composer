import unittest

from kafka_docker_composer import YamlGenerator
from argparse import Namespace
import os.path


class TestYamlGenerator(unittest.TestCase):
    def setUp(self) -> None:
        args = Namespace()
        setattr(args, "docker_compose_template", os.path.join("templates","docker-compose.template") )
        self.generator = YamlGenerator(args)


class TestOffset(TestYamlGenerator):
    def testSimpleOffset(self):
        placeholder="{{myservice}}"
        offset="   "
        template=[ "services:", offset + placeholder]

        found = YamlGenerator.find_offset(template, placeholder)
        self.assertEqual(offset, found)
