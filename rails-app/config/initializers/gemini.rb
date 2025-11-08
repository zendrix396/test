begin
  require 'gemini-ai'

  Gemini.configure do |config|
    # Prefer ENV for easier Windows setup; fallback to Rails credentials
    config.api_key = ENV['GOOGLE_API_KEY'] || Rails.application.credentials.dig(:google, :api_key)
  end
rescue LoadError => e
  Rails.logger.warn("Gemini AI not loaded: #{e.message}") if defined?(Rails)
end

