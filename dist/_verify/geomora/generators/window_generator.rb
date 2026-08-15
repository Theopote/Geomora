# frozen_string_literal: true

require_relative '../../geometry/units'
require_relative '../../geometry/vectors'
require_relative '../../metadata/attributes'
require_relative '../../components/component_manager'

module Geomora
  module Generators
    class WindowGenerator
      def initialize(model, component_manager:, tags:, project_id:, schema_version:)
        @model = model
        @component_manager = component_manager
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(window, wall, storey_elevation, parent_entities)
        definition_id = window.component&.fetch('definition_id', nil) ||
                        "window_#{window.width.to_i}"

        component_def = @component_manager.find_or_create(definition_id) do |definition|
          build_definition(definition, window)
        end

        transform = instance_transform(window, wall, storey_elevation)
        instance = parent_entities.add_instance(component_def, transform)
        instance.name = window.id

        Metadata::Attributes.write(instance, {
          entity_id: window.id,
          entity_type: window.type,
          schema_version: @schema_version,
          project_id: @project_id
        })

        @tags.apply(instance, 'Geomora_Windows')
        instance
      end

      private

      def build_definition(definition, window)
        ents = definition.entities
        width = window.width.to_f
        height = window.height.to_f
        frame = 50.0

        outer = [
          point(0, 0, 0),
          point(width, 0, 0),
          point(width, 0, height),
          point(0, 0, height)
        ]
        ents.add_face(outer)

        inner = [
          point(frame, 0, frame),
          point(width - frame, 0, frame),
          point(width - frame, 0, height - frame),
          point(frame, 0, height - frame)
        ]
        ents.add_face(inner)
      end

      def instance_transform(window, wall, storey_elevation)
        basis = Geometry::Vectors.wall_basis(wall.baseline)
        half_t = wall.thickness / 2.0

        offset = window.offset.to_f
        sill = window.sill_height.to_f

        along_pt = Geometry::Vectors.add(
          basis[:start],
          Geometry::Vectors.scale(basis[:along], offset)
        )

        ext_offset = Geometry::Vectors.scale(basis[:normal], half_t)
        origin = Geometry::Vectors.add(
          [along_pt[0], along_pt[1], storey_elevation + sill],
          ext_offset
        )

        x_axis = basis[:along]
        z_axis = basis[:up]
        y_axis = Geometry::Vectors.cross(z_axis, x_axis)

        Geom::Transformation.new(
          [
            to_len(x_axis[0]), to_len(y_axis[0]), to_len(z_axis[0]), to_len(origin[0]),
            to_len(x_axis[1]), to_len(y_axis[1]), to_len(z_axis[1]), to_len(origin[1]),
            to_len(x_axis[2]), to_len(y_axis[2]), to_len(z_axis[2]), to_len(origin[2]),
            0, 0, 0, 1
          ]
        )
      end

      def point(x, y, z)
        Geom::Point3d.new(to_len(x), to_len(y), to_len(z))
      end

      def to_len(mm)
        Geometry::Units.mm_to_length(mm)
      end
    end
  end
end
