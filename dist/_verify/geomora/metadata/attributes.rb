# frozen_string_literal: true

module Geomora
  module Metadata
    module Attributes
      DICTIONARY = 'geomora'

      class << self
        def write(entity, attrs)
          attrs.each do |key, value|
            entity.set_attribute(DICTIONARY, key.to_s, value)
          end
        end

        def read(entity, key)
          entity.get_attribute(DICTIONARY, key.to_s)
        end

        def geomora_entity?(entity)
          !read(entity, 'entity_id').nil?
        end

        def project_id(entity)
          read(entity, 'project_id')
        end
      end
    end
  end
end
