# frozen_string_literal: true

require_relative 'element_support'
require_relative '../geometry/polygon'

module Geomora
  module Generators
    class ColumnGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(column, storey_elevation, parent_entities)
        Logger.debug("Generating #{column.id}")

        group = parent_entities.add_group
        group.name = column.id
        origin = column.geometry[:position]
        width = column.geometry[:width].to_f
        depth = column.geometry[:depth].to_f
        height = column.geometry[:height].to_f
        z = storey_elevation + origin[2].to_f
        base = [origin[0], origin[1], z]
        polygon = Geometry::Polygon.rectangle_points(base, [width, 0, 0], [0, depth, 0])

        extrude_polygon(group.entities, polygon, height, direction: 1)
        write_metadata(group, column)
        @tags.apply(group, 'Geomora_Columns')
        group
      end
    end
  end
end
