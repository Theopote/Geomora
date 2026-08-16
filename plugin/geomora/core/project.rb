# frozen_string_literal: true

require 'json'

module Geomora
  module Core
    class Project
      def self.fixture_path
        File.join(plugin_root, 'examples', 'facade_phase0.json')
      end

      # Plugin root: plugin/geomora/ (dev) or Plugins/geomora/ (RBZ install)
      def self.plugin_root
        File.expand_path('..', __dir__)
      end

      def self.validate_file(path)
        validate_data(Loader.load_file(path))
        Logger.info("Validation passed: #{path}")
        true
      end

      def self.generate_from_file(path)
        data = Loader.load_file(path)
        generate_from_data(data)
      end

      def self.generate_from_data(data)
        document = parse_data(data)
        IR::Validator.validate(document)

        model = Sketchup.active_model
        Transactions::Operation.run('Geomora Generate', model) do
          Generators::ProjectGenerator.new(model).generate(document)
        end
      end

      def self.validate_data(data)
        document = parse_data(data)
        IR::Validator.validate(document)
        Logger.info('Validation passed')
        true
      end

      def self.analyze_pattern(params)
        PatternAnalyzer.analyze(params)
      end

      def self.rationalize_facade(params, grid_mm: Rationalizer::DEFAULT_GRID_MM)
        result = Rationalizer.rationalize(params, grid_mm: grid_mm)
        return result unless params['constraints'].is_a?(Array) && !params['constraints'].empty?

        solved = ConstraintSolver.solve(params.merge(result), grid_mm: grid_mm)
        result.merge(
          'windows' => solved['windows'],
          'door' => solved['door'],
          'constraint_solution' => solved['constraint_solution']
        )
      end

      def self.solve_constraints(params, grid_mm: Rationalizer::DEFAULT_GRID_MM)
        ConstraintSolver.solve(params, grid_mm: grid_mm)
      end

      def self.apply_lod_preset(preset)
        model = Sketchup.active_model
        label = LodScenes.apply_preset(model, preset)
        Logger.info("LOD preset applied: #{label}")
        label
      end

      def self.create_lod_scene_pages
        model = Sketchup.active_model
        pages = LodScenePages.create_pages(model)
        Logger.info("LOD scene pages created: #{pages.join(', ')}")
        pages
      end

      def self.next_lod_scene
        model = Sketchup.active_model
        LodPresentation.next_scene(model)
      end

      def self.lod_tour_manifest
        model = Sketchup.active_model
        LodPresentation.tour_manifest(model)
      end

      def self.export_lod_tour(path)
        model = Sketchup.active_model
        LodPresentation.export_tour_file(model, path)
      end

      def self.export_lod_tour_html(path, step_seconds: 2.0)
        model = Sketchup.active_model
        LodPresentation.export_tour_html(model, path, step_seconds: step_seconds)
      end

      def self.export_lod_tour_capture_html(path, step_seconds: 2.0)
        model = Sketchup.active_model
        LodPresentation.export_tour_capture_html(model, path, step_seconds: step_seconds)
      end

      def self.export_lod_tour_frames(directory)
        model = Sketchup.active_model
        LodPresentation.export_tour_frames(model, directory)
      end

      def self.fixture_catalog_diff(params = {})
        FixtureCatalog.diff(params)
      end

      def self.preview_room_layout(params)
        RoomLayoutEditor.preview(params)
      end

      def self.reload_fixture_catalog(params = {})
        FixtureCatalog.reload!(params)
      end

      def self.suggest_room_layout(params)
        RoomLayoutPresets.suggest(params)
      end

      def self.play_lod_tour(step_seconds: 2.0)
        model = Sketchup.active_model
        LodPresentation.play_tour(model, step_seconds: step_seconds)
      end

      def self.build_manual_facade(params)
        IRBuilder.build_manual_facade(params)
      end

      def self.load_and_parse(path)
        parse_data(Loader.load_file(path))
      end

      def self.parse_data(data)
        hash = data.is_a?(String) ? JSON.parse(data) : data
        IR::Parser.parse(hash)
      end

      def self.audit_geometry(options = {})
        GeometryDoctor.audit(options: options)
      end

      def self.repair_geometry(options = {})
        GeometryDoctor.repair(options: options)
      end
    end
  end
end
