# frozen_string_literal: true

ROOT = File.expand_path('../..', __dir__)
PLUGIN = File.join(ROOT, 'plugin', 'geomora')

$LOAD_PATH.unshift(PLUGIN) unless $LOAD_PATH.include?(PLUGIN)

require 'json'
require 'minitest/autorun'

# Stub SketchUp API for pure Ruby unit tests
unless defined?(Sketchup)
  module Sketchup; end

  module Geomora
    unless const_defined?(:Logger)
      # Logger already loaded below
    end
  end
end

require File.join(PLUGIN, 'version')
require File.join(PLUGIN, 'core/errors')
require File.join(PLUGIN, 'core/logger')
require File.join(PLUGIN, 'core/loader')
require File.join(PLUGIN, 'geometry/units')
require File.join(PLUGIN, 'geometry/vectors')
require File.join(PLUGIN, 'core/ir_builder')
require File.join(PLUGIN, 'core/building_composer')
require File.join(PLUGIN, 'core/detection_mapper')
require File.join(PLUGIN, 'core/structural_grid')
require File.join(PLUGIN, 'core/wall_enclosure')
require File.join(PLUGIN, 'core/interior_layout')
require File.join(PLUGIN, 'core/room_planner')
require File.join(PLUGIN, 'core/room_classifier')
require File.join(PLUGIN, 'core/furniture_planner')
require File.join(PLUGIN, 'core/room_overrides')
require File.join(PLUGIN, 'core/fixture_library')
require File.join(PLUGIN, 'core/room_layout')
require File.join(PLUGIN, 'core/furniture_collision')
require File.join(PLUGIN, 'core/furniture_orientation')
require File.join(PLUGIN, 'core/room_layout_presets')
require File.join(PLUGIN, 'core/room_layout_editor')
require File.join(PLUGIN, 'core/fixture_catalog')
require File.join(PLUGIN, 'core/perpendicular_constraint_solver')
require File.join(PLUGIN, 'core/structural_constraint_solver')
require File.join(PLUGIN, 'core/lod_presentation')
require File.join(PLUGIN, 'core/png_reader')
require File.join(PLUGIN, 'core/gif_encoder')
require File.join(PLUGIN, 'core/lod_capture')
require File.join(PLUGIN, 'core/layout_snap')
require File.join(PLUGIN, 'core/viewport_snapshot')
require File.join(PLUGIN, 'core/lod_video_exporter')
require File.join(PLUGIN, 'core/jpeg_frame_encoder')
require File.join(PLUGIN, 'core/mp4_encoder')
require File.join(PLUGIN, 'core/pdf_report_exporter')
require File.join(PLUGIN, 'core/avi_encoder')
require File.join(PLUGIN, 'core/viewport_stream')
require File.join(PLUGIN, 'core/layout_report_exporter')
require File.join(PLUGIN, 'core/constraint_solver')
require File.join(PLUGIN, 'core/lod_scenes')
require File.join(PLUGIN, 'core/lod_scene_pages')
require File.join(PLUGIN, 'core/lod_visibility')
require File.join(PLUGIN, 'core/lod_policy')
require File.join(PLUGIN, 'core/geometry_doctor')
require File.join(PLUGIN, 'core/rationalizer')
require File.join(PLUGIN, 'core/pattern_analyzer')
require File.join(PLUGIN, 'ir/models/document')
require File.join(PLUGIN, 'ir/parser')
require File.join(PLUGIN, 'ir/validator')
require File.join(PLUGIN, 'metadata/attributes')

module Geomora
  module TestHelper
    def load_fixture(name)
      path = File.join(ROOT, 'tests', 'fixtures', name)
      JSON.parse(File.read(path))
    end

    def parse_fixture(name)
      IR::Parser.parse(load_fixture(name))
    end

    def parse_example
      path = File.join(ROOT, 'examples', 'facade_phase0.json')
      data = JSON.parse(File.read(path))
      IR::Parser.parse(data)
    end
  end
end
