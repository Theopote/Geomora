# frozen_string_literal: true

require 'sketchup.rb'
require 'extensions.rb'

module Geomora
  EXTENSION_NAME = 'Geomora'
  EXTENSION_PATH = File.join(__dir__, 'geomora')

  unless file_loaded?(__FILE__)
    extension = SketchupExtension.new(
      EXTENSION_NAME,
      File.join(EXTENSION_PATH, 'extension.rb')
    )
    extension.description = 'Architectural geometry reconstruction for SketchUp'
    extension.version     = '0.19.0'
    extension.creator     = 'Geomora'
    Sketchup.register_extension(extension, true)
    file_loaded(__FILE__)
  end
end
