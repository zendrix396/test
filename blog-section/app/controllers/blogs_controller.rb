class BlogsController < ApplicationController
  include ActionController::Live
  before_action :set_blog, only: [:show, :edit, :update, :destroy]

  def index
    @blogs = Blog.all
  end

  def show
  end

  def new
    @blog = Blog.new
  end

  def edit
  end

  def create
    @blog = Blog.new(blog_params)

    if @blog.save
      redirect_to @blog, notice: "Blog was successfully created."
    else
      render :new, status: :unprocessable_entity
    end
  end

  def update
    if @blog.update(blog_params)
      redirect_to @blog, notice: "Blog was successfully updated."
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    @blog.destroy
    redirect_to blogs_url, notice: "Blog was successfully destroyed."
  end

  def new_generation
  end

  def create_generation
    titles = params[:titles].to_s.split(/\r?\n/).reject(&:blank?)
    
    if titles.empty?
      redirect_to generate_blogs_path, alert: "Please enter at least one title."
      return
    end

    prompt = "Generate a blog article for each of the following titles:\n\n"
    titles.each_with_index do |title, index|
      prompt += "#{index + 1}. \"#{title}\"\n"
    end
    prompt += "\nFor each title, provide a comprehensive and engaging article. The tone should be informative and accessible to a general programming audience. Separate each article with '---' on its own line."

    begin
      api_key = ENV['GOOGLE_API_KEY'] || Rails.application.credentials.dig(:google, :api_key)
      raise "Missing GOOGLE_API_KEY" if api_key.blank?

      require 'net/http'
      require 'json'
      uri = URI("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=#{api_key}")

      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = true
      request = Net::HTTP::Post.new(uri)
      request['Content-Type'] = 'application/json'
      request.body = {
        contents: [
          { parts: [ { text: prompt } ] }
        ]
      }.to_json

      response = http.request(request)
      body = JSON.parse(response.body) rescue {}
      if response.code.to_i >= 300
        message = body.dig('error', 'message') || "HTTP #{response.code}"
        raise("Gemini API error: #{message}")
      end

      generated_text = body.dig("candidates", 0, "content", "parts", 0, "text").to_s
      if generated_text.blank?
        raise "Empty response from Gemini"
      end

      generated_articles = generated_text.split("\n\n---\n\n")

      generated_articles.each_with_index do |article_content, index|
        break if index >= titles.size
        title = titles[index]
        Blog.create(title: title, content: article_content.strip)
      end

      redirect_to blogs_path, notice: "#{[generated_articles.size, titles.size].min} articles were successfully generated."
    rescue => e
      redirect_to generate_blogs_path, alert: "Error generating articles: #{e.message}"
    end
  end

  def stream_generation
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache, no-store"
    response.headers["X-Accel-Buffering"] = "no"

    sse = ActionController::Live::SSE.new(response.stream)

    blog_entries = params[:blog_entries] || []
    
    if blog_entries.empty?
      write_stream_event(sse, type: "error", message: "Please enter at least one title.")
      return
    end

    titles = []
    contexts = []
    
    blog_entries.each do |entry|
      title = entry[:title].to_s.strip
      context = entry[:context].to_s.strip
      
      next if title.blank?
      
      titles << title
      contexts << context
    end

    if titles.empty?
      write_stream_event(sse, type: "error", message: "Please enter at least one valid title.")
      return
    end

    write_stream_event(sse, type: "status", message: "Preparing prompt…")

    prompt = +"Generate blog articles for each of the following topics"
    
    has_context = contexts.any?(&:present?)
    
    if has_context
      prompt << " with their specific contexts"
    end
    
    prompt << ":\n\n"
    
    titles.each_with_index do |title, index|
      prompt << "#{index + 1}. Topic: \"#{title}\"\n"
      if contexts[index].present?
        prompt << "   Context: #{contexts[index]}\n"
      end
      prompt << "\n"
    end
    
    prompt << %(\nCRITICAL FORMAT REQUIREMENTS (MUST FOLLOW EXACTLY):

For EACH topic, you MUST generate:
1. A catchy, SEO-friendly title (different from the topic provided)
2. The full article content

Use EXACTLY these markers and format:

----BEGIN----
----TITLE----
[Your generated catchy title here]
----CONTENT----
[Your article content here - write naturally without preambles like "Here's an article about..."]
----END----

STRICT RULES:
- DO NOT write "Here's a blog about..." or "This article discusses..." - start directly with the content
- DO NOT include the topic name as the title - create a NEW catchy title
- MUST use ----TITLE---- separator before the title
- MUST use ----CONTENT---- separator before the content
- Each article MUST start with ----BEGIN---- and end with ----END----
- If context is provided, incorporate those guidelines in the article
- Keep tone natural, human-like, and engaging
- Make it informative and accessible

EXAMPLE FORMAT:
----BEGIN----
----TITLE----
10 Proven Strategies to Supercharge Your Development Workflow
----CONTENT----
In today's fast-paced development environment, efficiency is everything...
[rest of article content]
----END----

Generate comprehensive articles following this EXACT format.)

    api_key = ENV["GOOGLE_API_KEY"] || Rails.application.credentials.dig(:google, :api_key)
    if api_key.blank?
      write_stream_event(sse, type: "error", message: "Missing GOOGLE_API_KEY configuration.")
      return
    end

    require "net/http"
    require "json"
    uri = URI("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key=#{api_key}")
    request_body = {
      contents: [
        { parts: [{ text: prompt }] }
      ]
    }

    aggregated_text = +""
    current_article = +""
    article_index = 0
    in_article = false
    finished = false
    had_error = false
    saved = 0

    write_stream_event(sse, type: "status", message: "Contacting Gemini…")

    Net::HTTP.start(uri.host, uri.port, use_ssl: true, read_timeout: 120) do |http|
      request = Net::HTTP::Post.new(uri)
      request["Content-Type"] = "application/json"
      request.body = request_body.to_json

      http.request(request) do |res|
        unless res.is_a?(Net::HTTPSuccess)
          error_payload = +""
          res.read_body { |chunk| error_payload << chunk }
          message = begin
            parsed = JSON.parse(error_payload)
            parsed.dig("error", "message") || "HTTP #{res.code}"
          rescue JSON::ParserError
            "HTTP #{res.code}"
          end
          write_stream_event(sse, type: "error", message: "Gemini API error: #{message}")
          finished = true
          had_error = true
          break
        end

        buffer = +""

        res.read_body do |chunk|
          buffer << chunk

          while (newline_index = buffer.index("\n"))
            line = buffer.slice!(0, newline_index + 1).strip
            
            next if line.empty?
            
            if line.start_with?("data: ")
              payload = line[6..-1].strip
              
              next if payload.empty?
              
              if payload == "[DONE]"
                finished = true
                break
              end

              begin
                parsed = JSON.parse(payload)
                text_chunks = extract_text_chunks(parsed)
                
                text_chunks.each do |chunk_text|
                  aggregated_text << chunk_text
                  
                  write_stream_event(sse, type: "delta", text: chunk_text)
                  
                  if aggregated_text.include?("----BEGIN----") && !in_article
                    in_article = true
                    aggregated_text.sub!(/.*?----BEGIN----/m, "")
                    current_article = +""
                    write_stream_event(sse, type: "article_start", index: article_index, title: "Generating...")
                  end
                  
                  if in_article && aggregated_text.include?("----END----")
                    content_match = aggregated_text.match(/(.*?)----END----/m)
                    if content_match
                      current_article << content_match[1]
                      
                      article_text = current_article.strip
                      
                      title_match = article_text.match(/----TITLE----\s*(.*?)\s*----CONTENT----/m)
                      
                      if title_match
                        extracted_title = title_match[1].strip
                        content_start = article_text.index("----CONTENT----") + "----CONTENT----".length
                        extracted_content = article_text[content_start..-1].strip
                      else
                        extracted_title = titles[article_index] if article_index < titles.size
                        extracted_content = article_text.gsub(/----TITLE----/, "").gsub(/----CONTENT----/, "").strip
                      end
                      
                      if extracted_title.present? && extracted_content.present?
                        blog = Blog.create(
                          title: extracted_title,
                          content: extracted_content
                        )
                        saved += 1
                        write_stream_event(sse, type: "article_saved", index: article_index + 1, title: extracted_title, blog_id: blog.id)
                      end
                      
                      aggregated_text.sub!(/.*?----END----/m, "")
                      current_article = +""
                      article_index += 1
                      in_article = false
                    end
                  elsif in_article
                    current_article << chunk_text
                  end
                end
              rescue JSON::ParserError => e
                Rails.logger.warn("[stream_generation] Failed to parse SSE payload: #{e.message}")
                next
              end
            end
          end

          break if finished
        end
      end
    end

    return if had_error

    if saved == 0
      write_stream_event(sse, type: "error", message: "No articles were generated. Please try again.")
      return
    end

    write_stream_event(sse, type: "complete", saved: saved, requested: titles.size)
  rescue ActionController::Live::ClientDisconnected
    Rails.logger.info("[stream_generation] client disconnected")
  rescue => e
    Rails.logger.error("[stream_generation] #{e.class}: #{e.message}")
    write_stream_event(sse, type: "error", message: e.message) if sse
  ensure
    begin
      write_stream_event(sse, type: "done") if sse
    rescue IOError, ActionController::Live::ClientDisconnected
    ensure
      sse.close if sse
    end
  end

  private
    def set_blog
      @blog = Blog.find(params[:id])
    end

    def blog_params
      params.require(:blog).permit(:title, :content)
    end

    def write_stream_event(sse, payload)
      sse.write(payload)
    rescue IOError, ActionController::Live::ClientDisconnected
      raise
    end

    def extract_sse_payload(event_raw)
      data_lines = event_raw.to_s.each_line.select { |line| line.start_with?("data:") }
      return if data_lines.empty?
      payload = data_lines.map { |line| line.sub(/^data:\s?/, "") }.join("\n").strip
      payload.presence
    end

    def extract_text_chunks(parsed)
      Array(parsed["candidates"]).flat_map do |candidate|
        parts = candidate.dig("content", "parts") || []
        parts.filter_map { |part| part["text"] if part["text"].present? }
      end
    end
end

