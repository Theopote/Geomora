# frozen_string_literal: true

require 'json'

module Geomora
  module Core
    class FixtureCatalog
      DEFAULT_PATH = File.expand_path('../catalogs/default_fixtures.json', __dir__)

      @cache = {}

      class << self
        attr_accessor :cache
      end

      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['fixture_catalog'] || config[:fixture_catalog]
        value != false && value.to_s != 'false'
      end

      def self.items_for(room_type, params)
        return [] unless enabled?(params)

        catalog = load_catalog(params)
        catalog_sets = catalog['sets'] || {}
        normalize_items(catalog_sets[room_type.to_s])
      end

      def self.load_catalog(params, force: false)
        path = catalog_path(params)
        return empty_catalog unless path && File.exist?(path)

        cache_key = File.expand_path(path)
        unless force
          cached = (@cache || {})[cache_key]
          return cached if cached
        end

        data = JSON.parse(File.read(path))
        catalog = data.is_a?(Hash) ? data : empty_catalog
        @cache ||= {}
        @cache[cache_key] = catalog
        catalog
      rescue JSON::ParserError => e
        Logger.warn("Fixture catalog parse error: #{e.message}")
        empty_catalog
      end

      def self.reload!(params = {})
        clear_cache!
        catalog = load_catalog(params, force: true)
        Logger.info("Fixture catalog reloaded: #{catalog_path(params)}")
        catalog
      end

      def self.clear_cache!
        @cache = {}
      end

      def self.catalog_path(params)
        custom = params['fixture_catalog_path'] || params[:fixture_catalog_path]
        return custom if custom && !custom.to_s.strip.empty?

        DEFAULT_PATH
      end

      def self.empty_catalog
        { 'version' => '1.0', 'sets' => {} }
      end

      def self.normalize_items(items)
        return [] unless items.is_a?(Array)

        items.map do |item|
          next unless item.is_a?(Hash)

          {
            kind: item['kind'].to_s,
            width: item['width'].to_f,
            depth: item['depth'].to_f,
            height: item['height'].to_f,
            anchor: item['anchor'] || 'front_left',
            category: item['category'] || 'furniture',
            offset: item['offset']
          }.compact
        end.compact
      end
    end
  end
end
