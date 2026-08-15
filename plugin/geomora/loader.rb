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
    generators/opening_generator
    generators/window_generator
    generators/door_generator
    generators/storey_generator
    generators/building_generator
    generators/project_generator
    perception/rectification_result
    perception/rectify_client
    perception/detection_result
    perception/detect_client
    core/detection_mapper
    core/rationalizer
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
