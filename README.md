# AI-Powered Personalized News Recommendation System

## Overview
This system provides users with personalized news recommendations based on their interests. It combines web crawling, NLP-based content analysis, and machine learning to deliver tailored news content.

### Key Features
- **Automated News Crawling**: Scrape news articles from specified websites
- **AI-powered Tagging**: Use DeepSeek API for semantic content analysis
- **User Profiling**: Track user preferences through tag interaction
- **Personalized Recommendations**: Recommend news based on tag visit frequency
- **Real-time Dashboard**: Visualize user activity and recommendations

## Getting Started
### Prerequisites
- Python 3.8+
- MySQL Server
- Redis (Optional for caching)
- Docker (Recommended for deployment)

### Installation
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Configure environment variables:
```bash
export SECRET_KEY='your_secret_key'
export DATABASE_URL=''
export DEEPESEE_API_KEY='your_api_key'
```
3. Initialize database:
```bash
python manage.py migrate
```
4. Run development server:
```bash
python manage.py runserver
```
## Usage
### User Authentication
- Register new account: `/register`
- Login: `/login`
- Logout: `/logout`

### Dashboard
- Access personalized news feed: `/dashboard`
- View recommended news based on tag interactions

### API Endpoints
| Endpoint               | Method | Description                  |
|------------------------|--------|------------------------------|
| /api/news/recommend    | GET    | Get personalized news list   |
| /api/news/search       | GET    | Search news by keywords      |
| /api/tags/update       | POST   | Update tag visit counts      |

## Architecture


1. **Crawler Service**: Extracts news content using newspaper3k and BeautifulSoup
2. **NLP Service**: Performs semantic content analysis using DeepSeek API
3. **Recommendation Engine**: Calculates tag relevance scores
4. **Web Application**: Django-based frontend with RESTful APIs

## Contribution Guidelines
1. Fork the repository
2. Create feature branches
3. Write unit tests for new features
4. Submit pull requests
