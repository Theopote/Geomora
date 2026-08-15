# frozen_string_literal: true

require 'sketchup.rb'

module Geomora
  ROOT = File.expand_path(__dir__)

  %w[
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
    core/project
    ui/commands
  ].each do |file|
    require File.join(ROOT, file)
  end

  unless file_loaded?(__FILE__)
    UI::Commands.register
    file_loaded(__FILE__)
  end
end
