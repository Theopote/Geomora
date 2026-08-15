# frozen_string_literal: true

module Geomora
  class GeomoraError < StandardError; end
  class IRValidationError < GeomoraError; end
  class UnsupportedSchemaError < GeomoraError; end
  class GeometryGenerationError < GeomoraError; end
  class ReferenceResolutionError < GeomoraError; end
end
