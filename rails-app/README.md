# Gemini Blog & Twilio Call Manager

A Ruby on Rails application that combines AI-powered blog generation with automated call testing capabilities.

## Features

### 📝 Blog Management
- Create, read, update, and delete blog articles
- AI-powered blog generation using Google Gemini 2.5 Flash
- Real-time streaming blog generation with live preview
- Markdown support with syntax highlighting
- Modern, minimalist UI

### 📞 Call Testing
- Make automated test calls using Twilio
- Track call logs with detailed status information
- Support for multiple phone numbers (batch calling)
- Twilio magic test numbers for development
- Clean call history management

## Setup

### Prerequisites
- Ruby 3.3+ (see `.ruby-version`)
- Rails 8.1+
- SQLite3

### Installation

1. Clone the repository and install dependencies:
```bash
bundle install
```

2. Set up the database:
```bash
rails db:migrate
```

3. Configure environment variables:
```bash
# For Blog Generation
GOOGLE_API_KEY=your_google_gemini_api_key

# For Call Testing
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+15005550006  # Optional
```

4. Start the server:
```bash
rails server
```

5. Visit http://localhost:3000

## Usage

### Blog Section
- **Home**: View all blog articles at `/blogs` (root)
- **Generate Blogs**: AI-powered generation at `/generate_blogs`
- **New Blog**: Manual creation at `/blogs/new`

### Call Section
- **Call Logs**: View call history at `/calls`
- **Make Calls**: Initiate test calls at `/calls/new`

## Routes

```
# Blog Routes
GET    /blogs                    - List all blogs
POST   /blogs                    - Create blog
GET    /blogs/new                - New blog form
GET    /blogs/:id/edit           - Edit blog form
GET    /blogs/:id                - Show blog
PATCH  /blogs/:id                - Update blog
DELETE /blogs/:id                - Delete blog
GET    /generate_blogs           - Generate blogs form
POST   /generate_blogs/stream    - Stream generate blogs

# Call Routes
GET    /calls                    - View call logs
GET    /calls/new                - Make calls form
POST   /calls                    - Create calls
DELETE /calls/:id                - Delete call log
DELETE /calls_clear_all          - Clear all logs
```

## Technology Stack
- **Framework**: Ruby on Rails 8.1
- **Database**: SQLite3
- **AI**: Google Gemini 2.5 Flash API
- **Telephony**: Twilio REST API
- **Styling**: Custom CSS with design system
- **Markdown**: Redcarpet
