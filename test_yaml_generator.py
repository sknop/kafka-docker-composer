import unittest

from kafka_docker_composer import DockerComposeGenerator


class TestYamlGenerator(unittest.TestCase):
    def setUp(self):
        pass


class TestNextRack(TestYamlGenerator):
    def testSimpleAdd(self):
        rack = 0
        next = DockerComposeGenerator.next_rack(rack, 2)
        self.assertEqual(next, 1)

    def testOne(self):
        rack = 0
        next = DockerComposeGenerator.next_rack(rack, 1)
        self.assertEqual(next, 0)

    def testTotalRollover(self):
        rack = 1
        next = DockerComposeGenerator.next_rack(rack, 2)
        self.assertEqual(next, 0)
