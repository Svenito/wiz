# :coding: utf-8

import copy
import base64
import hashlib

import pytest

import wiz.definition
import wiz.utility
from wiz.utility import Requirement


@pytest.fixture()
def mocked_extract_version_ranges(mocker):
    """Return mocked wiz.utility.extract_version_ranges function."""
    return mocker.patch.object(wiz.utility, "extract_version_ranges")


@pytest.mark.parametrize("element", [
    "This is a string",
    42,
    ["This", "is", "a", "list"],
    {"key": "value"},
    {
        "key1": ["This", "is", "a", "list", 42],
        "key2": {"test": "This is a test"},
        "key3": 1337
    }
], ids=[
    "string",
    "number",
    "list",
    "dict",
    "complex-dict",
])
def test_encode_and_decode(element):
    """Encode *element* and immediately decode it."""
    encoded = wiz.utility.encode(element)
    assert isinstance(encoded, bytes)
    assert element == wiz.utility.decode(encoded)


@pytest.mark.parametrize("ranges1, ranges2, expected", [
    (
        [(None, None)],
        [(None, None)],
        True
    ),
    (
        [(None, None)],
        [((1, 1), (4,))],
        True
    ),
    (
        [((1, 1), (4,))],
        [(None, None)],
        True
    ),
    (
        [((1, 1), (4,))],
        [((1, 1), (4,))],
        True
    ),
    (
        [((4,), (4,))],
        [((1, 1), (4,))],
        True
    ),
    (
        [((5,), (7,))],
        [((4,), (4,))],
        False
    ),
    (
        [((4,), (4,))],
        [((5,), (7,))],
        False
    )
], ids=[
    "yes-no-boundaries",
    "yes-no-boundaries-left",
    "yes-no-boundaries-right",
    "yes-same-ranges",
    "yes-one-version-in",
    "no-out-of-scope-left",
    "no-out-of-scope-right"

])
def test_is_overlapping(
    mocker, mocked_extract_version_ranges, ranges1, ranges2, expected
):
    """Indicates whether requirements are overlapping."""
    req1 = mocker.Mock()
    req2 = mocker.Mock()

    # Hack due to the impossibility to directly mock an attribute called "name"
    # See: https://bradmontgomery.net/blog/how-world-do-you-mock-name-attribute
    type(req1).name = mocker.PropertyMock(return_value="foo")
    type(req2).name = mocker.PropertyMock(return_value="foo")

    mocked_extract_version_ranges.side_effect = [ranges1, ranges2]
    assert wiz.utility.is_overlapping(req1, req2) == expected


def test_is_overlapping_fail(mocker):
    """Fail to compare requirement with different name."""
    req1 = mocker.Mock()
    req2 = mocker.Mock()

    # Hack due to the impossibility to directly mock an attribute called "name"
    # See: https://bradmontgomery.net/blog/how-world-do-you-mock-name-attribute
    type(req1).name = mocker.PropertyMock(return_value="foo")
    type(req2).name = mocker.PropertyMock(return_value="bar")

    with pytest.raises(wiz.exception.GraphResolutionError) as error:
        wiz.utility.is_overlapping(req1, req2)

    assert (
        "Impossible to compare requirements with different names "
        "['foo' and 'bar']."
    ) in str(error)


@pytest.mark.parametrize("requirement, expected", [
    (
        Requirement("foo"),
        [(None, None)]
    ),
    (
        Requirement("foo <=0.1.0"),
        [(None, (0, 1, 0))]
    ),
    (
        Requirement("foo >=0.1.0"),
        [((0, 1, 0), None)]
    ),
    (
        Requirement("foo >=0.1.0, <=1"),
        [((0, 1, 0), (1,))]
    ),
    (
        Requirement("foo <0.1.0"),
        [(None, (0, 0, 9999))]
    ),
    (
        Requirement("foo >0.1.0"),
        [((0, 1, 0, 1), None)]
    ),
    (
        Requirement("foo >0.1.0, <1"),
        [((0, 1, 0, 1), (0, 9999,))]
    ),
    (
        Requirement("foo >=0.1.0, <1"),
        [((0, 1, 0), (0, 9999,))]
    ),
    (
        Requirement("foo ==0.1.0"),
        [((0, 1, 0), (0, 1, 0))]
    ),
    (
        Requirement("foo ==0.1.*"),
        [((0, 1), (0, 1, 9999))]
    ),
    (
        Requirement("foo ~=0.5"),
        [((0, 5), (0, 5, 9999))]
    ),
    (
        Requirement("foo !=0.3.9"),
        [(None, (0, 3, 8, 9999)), ((0, 3, 9, 1), None)]
    ),
    (
        Requirement("foo !=0.3.*"),
        [(None, (0, 2, 9999)), ((0, 4), None)]
    ),
    (
        Requirement("foo >=9, >3, >10, <=100, <19, !=11.*, !=11.0.*"),
        [((10, 1), (10, 9999)), ((12,), (18, 9999))]
    ),
    (
        Requirement("foo !=1.*, !=1.0.0, <2, ==0.1.0"),
        [((0, 1, 0), (0, 1, 0))]
    )
], ids=[
    "none",
    "inclusive-comparison",
    "inclusive-comparison-min",
    "inclusive-comparison",
    "exclusive-comparison-max",
    "exclusive-comparison-min",
    "exclusive-comparison",
    "mixed-comparison",
    "version-matching",
    "version-matching-with-wildcard",
    "compatible-release",
    "version-exclusion",
    "version-exclusion-with-wildcard",
    "mixed-1",
    "mixed-2"
])
def test_extract_version_ranges(requirement, expected):
    """Extract version ranges from requirements."""
    assert wiz.utility.extract_version_ranges(requirement) == expected


@pytest.mark.parametrize("requirement, expected", [
    (
        Requirement("foo ===8"),
        "Operator '===' is not accepted for requirement 'foo ===8'"
    ),
    (
        Requirement("foo >=9, <8"),
        "The requirement is incorrect as minimum value '9' cannot be set "
        "when maximum value is '7.9999'."
    ),
    (
        Requirement("foo >=8, <8"),
        "The requirement is incorrect as minimum value '8' cannot be set "
        "when maximum value is '7.9999'."
    ),
    (
        Requirement("foo ==1, ==2"),
        "The requirement is incorrect as minimum value '2' cannot be set "
        "when maximum value is '1'."
    ),
    (
        Requirement("foo ==1, !=1.*"),
        "The requirement is incorrect as excluded version range '0.9999-2' "
        "makes all other versions unreachable."
    )
], ids=[
    "incorrect-operator",
    "incorrect-comparison-1",
    "incorrect-comparison-2",
    "incorrect-comparison-3",
    "incorrect-exclusion"
])
def test_extract_version_ranges_error(requirement, expected):
    """Fail to extract version ranges from requirements."""
    with pytest.raises(wiz.exception.InvalidRequirement) as error:
        wiz.utility.extract_version_ranges(requirement)

    assert expected in str(error)


@pytest.mark.parametrize("version, ranges, expected", [
    (
        (1,),
        [(None, None)],
        [((1,), None)]
    ),
    (
        (1, 3, 3),
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 4))],
        [((1, 3, 3), (1, 4))]
    ),
    (
        (1, 2, 9),
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 4))],
        [((1, 2, 9), (1, 3, 0)), ((1, 3, 3), (1, 4))],
    ),
    (
        (1,),
        [(None, (0, 9999)), ((2,), None)],
        [((2,), None)]
    ),
    (
        (1,),
        [(None, (1, 1, 0))],
        [((1,), (1, 1, 0))]
    ),
    (
        (1, 0, 0),
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 4))],
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 4))],
    ),
], ids=[
    "minimal",
    "simple-01",
    "simple-02",
    "simple-03",
    "simple-04",
    "unchanged",
])
def test_update_minimum_version(version, ranges, expected):
    """Update range with minimum value."""
    wiz.utility._update_minimum_version(version, ranges)
    assert ranges == expected


def test_update_minimum_version_fail():
    """Fail to update range with minimum value."""
    with pytest.raises(wiz.exception.InvalidRequirement) as error:
        wiz.utility._update_minimum_version((1, 2, 3), [(None, (1,))])

    assert (
        "The requirement is incorrect as minimum value '1.2.3' cannot be set "
        "when maximum value is '1'."
    ) in str(error)


@pytest.mark.parametrize("version, ranges, expected", [
    (
        (1,),
        [(None, None)],
        [(None, (1,))]
    ),
    (
        (1, 3, 3),
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 4))],
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 3, 3))]
    ),
    (
        (1, 2, 9),
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 4))],
        [((1, 2, 3), (1, 2, 9))],
    ),
    (
        (1,),
        [(None, (0, 9999)), ((2,), None)],
        [(None, (0, 9999))]
    ),
    (
        (1,),
        [((0, 1, 0), None)],
        [((0, 1, 0), (1,))]
    ),
    (
        (2, 0, 0),
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 4))],
        [((1, 2, 3), (1, 3, 0)), ((1, 3, 3), (1, 4))],
    ),
], ids=[
    "minimal",
    "simple-01",
    "simple-02",
    "simple-03",
    "simple-04",
    "unchanged",
])
def test_update_maximum_version(version, ranges, expected):
    """Update range with minimum value."""
    wiz.utility._update_maximum_version(version, ranges)
    assert ranges == expected


def test_update_maximum_version_fail():
    """Fail to update range with maximum value."""
    with pytest.raises(wiz.exception.InvalidRequirement) as error:
        wiz.utility._update_maximum_version((1, 2, 3), [((2,), None)])

    assert (
        "The requirement is incorrect as maximum value '1.2.3' cannot be set "
        "when minimum value is '2'."
    ) in str(error)


@pytest.mark.parametrize("excluded, ranges, expected", [
    (
        ((1,), (2,)),
        [(None, None)],
        [(None, (1,)), ((2,), None)]
    ),
    (
        ((1,), (2,)),
        [((0,), (3,))],
        [((0,), (1,)), ((2,), (3,))]
    ),
    (
        ((1,), (2,)),
        [((1,), (2,))],
        [((1,), (1,)), ((2,), (2,))],
    ),
    (
        ((1,), (2,)),
        [(None, (1, 2, 3))],
        [(None, (1,))]
    ),
    (
        ((1,), (2,)),
        [((1, 2, 3), None)],
        [((2,), None)]
    ),
    (
        ((1,), (2,)),
        [((2,), (3,))],
        [((2,), (3,))],
    ),
    (
        ((4,), (5,)),
        [((2,), (3,))],
        [((2,), (3,))],
    ),
], ids=[
    "exclude-middle-range-01",
    "exclude-middle-range-02",
    "exclude-middle-range-03",
    "exclude-end-range",
    "exclude-start-range",
    "out-of-range-01",
    "out-of-range-02",
])
def test_update_version_ranges(excluded, ranges, expected):
    """Update version ranges from excluded version range."""
    wiz.utility._update_version_ranges(excluded, ranges)
    assert ranges == expected


def test_update_version_ranges_fail():
    """Fail to update version ranges from excluded version range."""
    with pytest.raises(wiz.exception.InvalidRequirement) as error:
        wiz.utility._update_version_ranges(((0,), (3,)), [((1,), (2,))])

    assert (
        "The requirement is incorrect as excluded version range '0-3' "
        "makes all other versions unreachable."
    ) in str(error)


@pytest.mark.parametrize("definition, expected", [
    (
        wiz.definition.Definition({"identifier": "test"}),
        "'test'"
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "version": "0.1.0"
        }),
        "'test' [0.1.0]"
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "namespace": "foo"
        }),
        "'foo::test'"
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "system": {
                "platform": "linux"
            }
        }),
        "'test' (linux)"
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "version": "0.1.0",
            "namespace": "foo",
            "system": {
                "platform": "linux"
            }
        }),
        "'foo::test' [0.1.0] (linux)"
    )
], ids=[
    "simple",
    "with-version",
    "with-namespace",
    "with-system",
    "with-all",
])
def test_compute_label(definition, expected):
    """Compute definition label."""
    assert wiz.utility.compute_label(definition) == expected


@pytest.mark.parametrize("definition, expected", [
    (
        wiz.definition.Definition({"identifier": "test"}),
        "test.json"
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "version": "0.1.0"
        }),
        "test-0.1.0.json"
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "namespace": "foo"
        }),
        "foo-test.json"
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "namespace": "foo::bar::bim"
        }),
        "foo-bar-bim-test.json"
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "system": {
                "platform": "linux"
            }
        }),
        "test-{}.json".format(
            base64.urlsafe_b64encode(
                hashlib.sha1(b"linux").digest()
            ).rstrip(b"=").decode("utf-8")
        )
    ),
    (
        wiz.definition.Definition({
            "identifier": "test",
            "version": "0.1.0",
            "namespace": "bar::foo",
            "system": {
                "platform": "linux"
            }
        }),
        "bar-foo-test-0.1.0-{}.json".format(
            base64.urlsafe_b64encode(
                hashlib.sha1(b"linux").digest()
            ).rstrip(b"=").decode("utf-8")
        )
    )
], ids=[
    "simple",
    "with-version",
    "with-namespace",
    "with-multiple-namespaces",
    "with-system",
    "with-all",
])
def test_compute_file_name(definition, expected):
    """Compute definition file name."""
    assert wiz.utility.compute_file_name(definition) == expected


@pytest.mark.parametrize("mapping1, mapping2, expected", [
    ({}, {}, {}),
    ({"A": 1, "B": 2}, {"B": 3}, {"A": 1, "B": 3}),
    (
        {"A": 1, "B": {"C": 3, "D": 4}},
        {"B": {"C": 4}},
        {"A": 1, "B": {"C": 4, "D": 4}},
    ),
    (
        {"A": 1, "B": {"C": {"D": 4, "E": 5}}},
        {"B": {"C": {"E": 6}}},
        {"A": 1, "B": {"C": {"D": 4, "E": 6}}},
    ),
    (
        {"A": 1, "B": {"C": {"D": {"E": {"F": {"G": 2, "H": 3}}}}}},
        {"B": {"C": {"D": {"E": {"F": {"H": 4, "I": 5}}}}}},
        {"A": 1, "B": {"C": {"D": {"E": {"F": {"G": 2, "H": 4, "I": 5}}}}}},
    )
], ids=[
    "empty",
    "simple",
    "one-level-deep",
    "two-level-deep",
    "five-level-deep"
])
def test_deep_update(mapping1, mapping2, expected):
    """Recursively update mapping."""
    _mapping2 = copy.deepcopy(mapping2)
    assert wiz.utility.deep_update(mapping1, mapping2) == expected
    assert mapping1 == expected
    assert mapping2 == _mapping2
