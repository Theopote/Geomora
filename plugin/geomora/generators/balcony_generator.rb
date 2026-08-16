# frozen_string_literal: true

require_relative 'element_support'
require_relative '../geometry/polygon'

module Geomora
  module Generators
    class BalconyGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(balcony, storey_elevation, parent_entities)
        Logger.debug("Generating #{balcony.id}")

        group = parent_entities.add_group
        group.name = balcony.id
        origin = balcony.geometry[:position]
        width = balcony.geometry[:width].to_f
        depth = balcony.geometry[:depth].to_f
        thickness = balcony.geometry[:thickness].to_f
        direction = balcony.geometry[:direction].to_i
        depth_vec = [0, depth * direction, 0]
        z = storey_elevation + origin[2].to_f
        base = [origin[0], origin[1], z]
        polygon = Geometry::Polygon.rectangle_points(base, [width, 0, 0], depth_vec)

        extrude_polygon(group.entities, polygon, thickness, direction: 1)
        write_metadata(group, balcony)
        @tags.apply(group, 'Geomora_Balconies')
        group
      end
    end
  end
end
