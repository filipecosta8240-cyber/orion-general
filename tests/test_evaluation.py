"""Tests for evaluation framework"""
import pytest
from orion.evaluation import Evaluator, TestSuite, TestCase


def test_suite_registration():
    evaluator = Evaluator()
    suite = TestSuite(name="test_suite")
    suite.add_test(TestCase(name="test1", input_data={"q": "hello"}, expected_output="hello"))
    suite_id = evaluator.register_suite(suite)
    assert suite_id is not None


def test_suite_execution():
    evaluator = Evaluator()
    suite = TestSuite(name="exec_suite")
    suite.add_test(TestCase(name="t1", input_data={"x": 1}, expected_output="ok"))
    suite.add_test(TestCase(name="t2", input_data={"x": 2}, expected_output="ok"))
    evaluator.register_suite(suite)
    
    def handler(data):
        return "ok"
    
    result = evaluator.run_suite(suite.id, handler)
    assert result is not None
    assert result.pass_rate == 1.0
    assert len(result.results) == 2


def test_empty_suite():
    evaluator = Evaluator()
    suite = TestSuite(name="empty")
    evaluator.register_suite(suite)
    
    def handler(data):
        return "ok"
    
    result = evaluator.run_suite(suite.id, handler)
    assert result is not None
    assert result.pass_rate == 0.0
