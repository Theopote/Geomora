# frozen_string_literal: true

require_relative '../test_helper'

class UnitsTest < Minitest::Test
  def test_mm_to_mm
    assert_in_delta 1000.0, Geomora::Geometry::Units.to_mm(1000, 'mm'), 0.001
  end

  def test_mm_to_inches
    assert_in_delta 39.3700787, Geomora::Geometry::Units.mm_to_inches(1000), 0.001
  end

  def test_unsupported_unit_raises
    assert_raises(Geomora::UnsupportedSchemaError) do
      Geomora::Geometry::Units.to_mm(100, 'ft')
    end
  end

  def test_wall_length_10000mm
    data = JSON.parse(File.read(File.join(ROOT, 'examples', 'facade_phase0.json')))
    doc = Geomora::IR::Parser.parse(data)
    wall = doc.buildings.first.storeys.first.elements.first
    assert_in_delta 10_000.0, wall.length, 0.001
  end
end
