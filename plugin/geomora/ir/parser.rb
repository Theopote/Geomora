# frozen_string_literal: true

require_relative 'models/document'

module Geomora
  module IR
    class Parser
      OPENING_TYPES = %w[window door opening].freeze
      ELEMENT_TYPES = %w[wall floor roof column beam stair].freeze

      def self.parse(data)
        new(data).parse
      end

      def initialize(data)
        @data = data
      end

      def parse
        Models::Document.new(
          schema_version: @data['schema_version'],
          project: parse_project(@data['project']),
          buildings: (@data['buildings'] || []).map { |b| parse_building(b) },
          components: (@data['components'] || []).map { |c| parse_component(c) },
          constraints: (@data['constraints'] || []).map { |c| parse_constraint(c) },
          sources: (@data['sources'] || []).map { |s| parse_source(s) },
          openings: collect_openings
        )
      end

      private

      def parse_project(p)
        Models::Project.new(
          id: p['id'],
          name: p['name'],
          unit: p['unit'],
          coordinate_system: p['coordinate_system'],
          default_wall_thickness: p['default_wall_thickness']
        )
      end

      def parse_building(b)
        Models::Building.new(
          id: b['id'],
          name: b['name'],
          storeys: (b['storeys'] || []).map { |s| parse_storey(s) }
        )
      end

      def parse_storey(s)
        Models::Storey.new(
          id: s['id'],
          name: s['name'],
          elevation: s['elevation'],
          height: s['height'],
          elements: (s['elements'] || []).map { |e| parse_element(e) }
        )
      end

      def parse_element(e)
        case e['type']
        when 'wall' then parse_wall(e)
        when 'floor' then parse_floor(e)
        when 'roof' then parse_roof(e)
        when 'column' then parse_column(e)
        when 'beam' then parse_beam(e)
        when 'stair' then parse_stair(e)
        else
          raise UnsupportedSchemaError, "Unsupported element type: #{e['type']}"
        end
      end

      def parse_wall(w)
        Models::Wall.new(
          id: w['id'],
          type: w['type'],
          storey_id: w['storey_id'],
          geometry: symbolize_geometry(w['geometry']),
          semantic: w['semantic'] || {},
          opening_ids: w['opening_ids'] || [],
          confidence: w['confidence']
        )
      end

      def parse_floor(e)
        Models::Floor.new(
          id: e['id'],
          type: e['type'],
          storey_id: e['storey_id'],
          geometry: symbolize_geometry(e['geometry']),
          semantic: e['semantic'] || {},
          confidence: e['confidence']
        )
      end

      def parse_roof(e)
        Models::Roof.new(
          id: e['id'],
          type: e['type'],
          storey_id: e['storey_id'],
          geometry: symbolize_geometry(e['geometry']),
          semantic: e['semantic'] || {},
          confidence: e['confidence']
        )
      end

      def parse_column(e)
        Models::Column.new(
          id: e['id'],
          type: e['type'],
          storey_id: e['storey_id'],
          geometry: symbolize_geometry(e['geometry']),
          semantic: e['semantic'] || {},
          confidence: e['confidence']
        )
      end

      def parse_beam(e)
        Models::Beam.new(
          id: e['id'],
          type: e['type'],
          storey_id: e['storey_id'],
          geometry: symbolize_geometry(e['geometry']),
          semantic: e['semantic'] || {},
          confidence: e['confidence']
        )
      end

      def parse_stair(e)
        Models::Stair.new(
          id: e['id'],
          type: e['type'],
          storey_id: e['storey_id'],
          geometry: symbolize_geometry(e['geometry']),
          semantic: e['semantic'] || {},
          confidence: e['confidence']
        )
      end

      def collect_openings
        openings = @data['openings'] || []
        openings.map { |o| parse_opening(o) }
      end

      def parse_opening(o)
        Models::Opening.new(
          id: o['id'],
          type: o['type'],
          parent_id: o['parent_id'],
          geometry: symbolize_geometry(o['geometry']),
          component: o['component'],
          confidence: o['confidence'],
          source: o['source']
        )
      end

      def parse_component(c)
        Models::ComponentDef.new(
          id: c['id'],
          type: c['type'],
          parameters: c['parameters'] || {}
        )
      end

      def parse_constraint(c)
        Models::Constraint.new(
          id: c['id'],
          type: c['type'],
          targets: c['targets'] || [],
          priority: c['priority']
        )
      end

      def parse_source(s)
        Models::Source.new(
          id: s['id'],
          type: s['type'],
          metadata: s['metadata'] || {}
        )
      end

      def symbolize_geometry(geo)
        {
          baseline: geo['baseline'],
          height: geo['height'],
          thickness: geo['thickness'],
          offset: geo['offset'],
          sill_height: geo['sill_height'],
          width: geo['width'],
          depth: geo['depth'],
          polygon: geo['polygon'],
          elevation: geo['elevation'],
          position: geo['position'],
          origin: geo['origin'],
          run: geo['run'],
          rise: geo['rise'],
          steps: geo['steps']
        }.compact
      end
    end
  end
end
