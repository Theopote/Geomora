# frozen_string_literal: true

require_relative '../test_helper'

class ValidatorTest < Minitest::Test
  include Geomora::TestHelper

  def test_valid_phase0_fixture
    doc = parse_example
    assert Geomora::IR::Validator.validate(doc)
  end

  def test_unsupported_schema_version
    data = JSON.parse(File.read(File.join(ROOT, 'examples', 'facade_phase0.json')))
    data['schema_version'] = '9.9'
    doc = Geomora::IR::Parser.parse(data)

    error = assert_raises(Geomora::IRValidationError) { Geomora::IR::Validator.validate(doc) }
    assert_match(/Unsupported schema version/, error.message)
  end

  def test_duplicate_id
    doc = parse_fixture('invalid_duplicate_id.json')
    error = assert_raises(Geomora::IRValidationError) { Geomora::IR::Validator.validate(doc) }
    assert_match(/Duplicate entity ID/, error.message)
  end

  def test_invalid_parent
    doc = parse_fixture('invalid_parent.json')
    error = assert_raises(Geomora::IRValidationError) { Geomora::IR::Validator.validate(doc) }
    assert_match(/Invalid parent_id/, error.message)
  end

  def test_negative_dimension
    doc = parse_fixture('invalid_negative_dimension.json')
    error = assert_raises(Geomora::IRValidationError) { Geomora::IR::Validator.validate(doc) }
    assert_match(/Negative height/, error.message)
  end

  def test_opening_bounds
    doc = parse_fixture('invalid_opening_bounds.json')
    error = assert_raises(Geomora::IRValidationError) { Geomora::IR::Validator.validate(doc) }
    assert_match(/exceeds bounds/, error.message)
  end

  def test_opening_overlap_detection
    data = JSON.parse(File.read(File.join(ROOT, 'examples', 'facade_phase0.json')))
    data['openings'][1]['geometry']['offset'] = 1000
    doc = Geomora::IR::Parser.parse(data)

    error = assert_raises(Geomora::IRValidationError) { Geomora::IR::Validator.validate(doc) }
    assert_match(/Opening overlap/, error.message)
  end

  def test_door_below_window_is_not_overlap
    data = JSON.parse(File.read(File.join(ROOT, 'examples', 'facade_phase0.json')))
    data['openings'].find { |o| o['id'] == 'door_001' }['geometry']['offset'] = 500
    doc = Geomora::IR::Parser.parse(data)

    assert Geomora::IR::Validator.validate(doc)
  end

  def test_zero_length_wall
    data = JSON.parse(File.read(File.join(ROOT, 'examples', 'facade_phase0.json')))
    data['buildings'][0]['storeys'][0]['elements'][0]['geometry']['baseline'] = [[0, 0, 0], [0, 0, 0]]
    doc = Geomora::IR::Parser.parse(data)

    error = assert_raises(Geomora::IRValidationError) { Geomora::IR::Validator.validate(doc) }
    assert_match(/Zero-length wall/, error.message)
  end

  def test_unsupported_unit
    data = JSON.parse(File.read(File.join(ROOT, 'examples', 'facade_phase0.json')))
    data['project']['unit'] = 'ft'
    doc = Geomora::IR::Parser.parse(data)

    error = assert_raises(Geomora::IRValidationError) { Geomora::IR::Validator.validate(doc) }
    assert_match(/Unsupported unit/, error.message)
  end
end
