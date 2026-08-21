# frozen_string_literal: true

require_relative '../test_helper'
require File.join(PLUGIN, 'generators/opening_generator')

module Geom
  Point3d = Struct.new(:x, :y, :z) unless const_defined?(:Point3d)
end

class OpeningGeneratorTest < Minitest::Test
  include Geomora::TestHelper

  def setup
    @model = Object.new
    @generator = Geomora::Generators::OpeningGenerator.new(@model)
    @wall = Geomora::IR::Models::Wall.new(
    id: 'wall_001',
    type: 'wall',
    storey_id: 'storey_01',
    geometry: {
      baseline: [[0, 0, 0], [10_000, 0, 0]],
      height: 3300,
      thickness: 240
    },
    opening_ids: ['window_001']
    )
    @opening = Geomora::IR::Models::Opening.new(
    id: 'window_001',
    type: 'window',
    parent_id: 'wall_001',
    geometry: {
      offset: 1000,
      sill_height: 900,
      width: 1500,
      height: 1500,
      depth: 240
    },
    component: { definition_id: 'window_standard_1500' }
    )
  end

  def test_raises_when_opening_face_is_invalid
    wall_group = stub_wall_group(invalid_face: true)

    error = assert_raises(Geomora::GeometryGenerationError) do
      @generator.cut_openings(wall_group, @wall, [@opening], 0)
    end

    assert_match(/Failed to create opening window_001 in wall wall_001/, error.message)
  end

  def test_raises_when_add_face_returns_nil
    wall_group = stub_wall_group(return_nil: true)

    error = assert_raises(Geomora::GeometryGenerationError) do
      @generator.cut_openings(wall_group, @wall, [@opening], 0)
    end

    assert_match(/Failed to create opening window_001 in wall wall_001/, error.message)
  end

  def test_pushpulls_valid_opening_face
    wall_group = stub_wall_group(invalid_face: false, track_pushpull: true)

    @generator.cut_openings(wall_group, @wall, [@opening], 0)

    assert wall_group.entities.face.pushpull_called
  end

  private

  def stub_wall_group(return_nil: false, invalid_face: false, track_pushpull: false)
    face_stub = if return_nil
                  nil
                elsif invalid_face
                  build_face_stub(valid: false)
                else
                  build_face_stub(track_pushpull: track_pushpull)
                end

    entities = Object.new
    entities.define_singleton_method(:face) { face_stub }
    entities.define_singleton_method(:add_face) { |_pts| face_stub }

    wall_group = Object.new
    wall_group.define_singleton_method(:entities) { entities }
    wall_group
  end

  def build_face_stub(valid: true, track_pushpull: false)
    pushed = false
    face = Object.new
    face.define_singleton_method(:valid?) { valid }
    face.define_singleton_method(:pushpull) do |_depth|
      pushed = true
    end
    face.define_singleton_method(:pushpull_called) { pushed } if track_pushpull
    face
  end
end
