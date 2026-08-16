# frozen_string_literal: true

# Central loader — all paths relative to plugin/geomora/
module Geomora
  ROOT = File.expand_path(__dir__)

  LOADER_FILES = %w[
    version
    core/errors
    core/logger
    core/loader
    geometry/units
    geometry/vectors
    geometry/polygon
    ir/models/document
    ir/parser
    ir/validator
    metadata/attributes
    transactions/operation
    components/component_manager
    tags/manager
    generators/wall_generator
    generators/element_support
    generators/floor_generator
    generators/roof_generator
    generators/column_generator
    generators/beam_generator
    generators/stair_generator
    generators/balcony_generator
    generators/parapet_generator
    generators/cornice_generator
    generators/trim_generator
    generators/railing_generator
    generators/eaves_generator
    generators/room_generator
    generators/furniture_generator
    generators/opening_generator
    generators/window_generator
    generators/door_generator
    generators/storey_generator
    generators/wall_join_processor
    generators/building_generator
    generators/project_generator
    perception/rectification_result
    perception/rectify_client
    perception/detection_result
    perception/detect_client
    perception/multiview_result
    perception/multiview_client
    perception/fusion_result
    core/detection_mapper
    core/rationalizer
    core/pattern_analyzer
    core/building_composer
    core/lod_policy
    core/lod_visibility
    core/structural_grid
    core/wall_enclosure
    core/interior_layout
    core/room_planner
    core/room_classifier
    core/furniture_planner
    core/fixture_library
    core/room_layout
    core/furniture_collision
    core/furniture_orientation
    core/room_layout_presets
    core/room_layout_editor
    core/fixture_catalog
    core/perpendicular_constraint_solver
    core/room_overrides
    core/structural_constraint_solver
    core/lod_presentation
    core/lod_capture
    core/constraint_solver
    core/lod_scenes
    core/lod_scene_pages
    core/geometry_doctor
    core/ir_builder
    core/project
    ui/workspace_dialog
    ui/commands
  ].freeze

  def self.require_all
    LOADER_FILES.each do |file|
      path = File.join(ROOT, "#{file}.rb")
      unless File.exist?(path)
        raise LoadError, "Geomora missing file: #{path}"
      end
      require path
    end
  end
end

Geomora.require_all
