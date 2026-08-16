# frozen_string_literal: true

require_relative 'element_support'
require_relative '../geometry/polygon'

module Geomora
  module Generators
    class StairGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(stair, storey_elevation, parent_entities)
        Logger.debug("Generating #{stair.id}")

        group = parent_entities.add_group
        group.name = stair.id
        origin = stair.geometry[:origin]
        width = stair.geometry[:width].to_f
        run = stair.geometry[:run].to_f
        rise = stair.geometry[:rise].to_f
        steps = [stair.geometry[:steps].to_i, 1].max
        step_run = run / steps
        step_rise = rise / steps
        z_base = storey_elevation + origin[2].to_f

        steps.times do |index|
          step_group = group.entities.add_group
          step_group.name = "#{stair.id}_step_#{index + 1}"
          base = [
            origin[0] + (index * step_run),
            origin[1],
            z_base + (index * step_rise)
          ]
          polygon = Geometry::Polygon.rectangle_points(base, [step_run, 0, 0], [0, width, 0])
          extrude_polygon(step_group.entities, polygon, step_rise, direction: 1)
        end

        write_metadata(group, stair)
        @tags.apply(group, 'Geomora_Stairs')
        group
      end
    end
  end
end
