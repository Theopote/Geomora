# frozen_string_literal: true

module Geomora
  module IR
    module Models
      Project = Struct.new(
        :id, :name, :unit, :coordinate_system, :default_wall_thickness, :lod_level,
        keyword_init: true
      )

      Building = Struct.new(:id, :name, :storeys, keyword_init: true)

      Storey = Struct.new(
        :id, :name, :elevation, :height, :elements,
        keyword_init: true
      )

      Wall = Struct.new(
        :id, :type, :storey_id, :geometry, :semantic, :opening_ids, :confidence,
        keyword_init: true
      ) do
        def baseline
          geometry[:baseline]
        end

        def height
          geometry[:height]
        end

        def thickness
          geometry[:thickness]
        end

        def length
          bl = baseline
          dx = bl[1][0] - bl[0][0]
          dy = bl[1][1] - bl[0][1]
          dz = bl[1][2] - bl[0][2]
          Math.sqrt(dx**2 + dy**2 + dz**2)
        end
      end

      Floor = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Roof = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Column = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Beam = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Stair = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Balcony = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Parapet = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Cornice = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Trim = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Railing = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Eaves = Struct.new(:id, :type, :storey_id, :geometry, :semantic, :confidence, keyword_init: true)
      Room = Struct.new(:id, :storey_id, :name, :geometry, :semantic, :confidence, keyword_init: true)

      Opening = Struct.new(
        :id, :type, :parent_id, :geometry, :component, :confidence, :source,
        keyword_init: true
      ) do
        def offset
          geometry[:offset]
        end

        def width
          geometry[:width]
        end

        def height
          geometry[:height]
        end

        def sill_height
          geometry[:sill_height] || 0
        end

        def depth
          geometry[:depth]
        end
      end

      Window = Opening
      Door = Opening

      ComponentDef = Struct.new(
        :id, :type, :parameters, keyword_init: true
      )

      Constraint = Struct.new(
        :id, :type, :targets, :priority, keyword_init: true
      )

      Source = Struct.new(:id, :type, :metadata, keyword_init: true)

      Document = Struct.new(
        :schema_version, :project, :buildings, :components,
        :constraints, :sources, :openings, :rooms,
        keyword_init: true
      )
    end
  end
end
