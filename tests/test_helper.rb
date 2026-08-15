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
