import unittest

from kafka_docker_composer import YamlGenerator, OffsetNotFoundException

class TestYamlGenerator(unittest.TestCase):
    def setUp(self):
        pass

class TestOffset(TestYamlGenerator):
    def testSimpleOffset(self):
        placeholder="{{myservice}}"
        offset="   "
        template="\n".join([ "services:", offset + placeholder])

        found = YamlGenerator.find_offset(template, placeholder)
        self.assertEqual(offset, found)

    def testMissingOffset(self):
        placeholder="{{my-missing-service}}"
        fakeholder="{{my-fake-service}}"
        offset="   "
        template="\n".join([ "services:", offset + fakeholder])

        with self.assertRaises(OffsetNotFoundException):
            YamlGenerator.find_offset(template, placeholder)


class TestNextRack(TestYamlGenerator):
    def testSimpleAdd(self):
        rack = 0
        next = YamlGenerator.next_rack(rack,2)
        self.assertEqual(next,1)

    def testOne(self):
        rack = 0
        next = YamlGenerator.next_rack(rack,1)
        self.assertEqual(next,0)

    def testTotalRollover(self):
        rack = 1
        next = YamlGenerator.next_rack(rack,2)
        self.assertEqual(next, 0)
