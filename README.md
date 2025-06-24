# Claude Job Agent

> **Intelligent Job Search Assistant for Claude Desktop**

A powerful job search automation tool designed specifically for Claude Desktop, providing intelligent job discovery, application tracking, and career guidance without requiring external AI API costs.

## 🌟 Features

### Core Functionality

- **Multi-Source Job Aggregation** - Search across multiple job platforms (Adzuna, with extensible architecture)
- **Intelligent Job Analysis** - Structured frameworks for Claude to analyze job compatibility
- **Application Tracking** - Comprehensive tracking system with follow-up reminders
- **Career Progression Planning** - Personalized roadmaps and skill gap analysis
- **Market Intelligence** - Job market trends and salary insights

### Claude Desktop Optimized

- **Zero External AI Costs** - All analysis done by Claude Desktop's built-in AI
- **MCP Integration** - Native Model Context Protocol server
- **Structured Data** - Optimized data formats for Claude's analysis
- **Framework-Based Analysis** - Consistent scoring and evaluation templates

### Monitoring & Reliability

- **Health Monitoring** - Database and API connectivity checks
- **Performance Metrics** - Response time and success rate tracking
- **Automated Backups** - Regular database backups with retention policies
- **Error Logging** - Comprehensive error tracking and alerting

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Claude Desktop application
- Job search API credentials (Adzuna)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/claude-job-agent.git
   cd claude-job-agent
   ```

2. **Install dependencies**

   ```bash
   # Basic installation
   pip install -e .
   
   # Development installation with all extras
   pip install -e ".[all]"
   ```

3. **Configure environment variables**
   Create a `.env` file or set environment variables:

   ```bash
   ADZUNA_APP_ID=your_adzuna_app_id
   ADZUNA_APP_KEY=your_adzuna_app_key
   DATABASE_PATH=data/jobs.db  # Optional: custom database path
   ```

4. **Configure Claude Desktop**
   Add to your Claude Desktop configuration:

   ```json
   {
     "mcpServers": {
       "claude-job-agent": {
         "command": "uv",
         "args": [
            "--directory",
            "/path/to/claude-job-agent",
            "run",
            "src/claude_job_agent/main.py"
         ],
         "env": {
           "ADZUNA_APP_ID": "your_app_id",
           "ADZUNA_APP_KEY": "your_app_key",
           "DATABASE_PATH": "/path/to/jobs.db"
         }
       }
     }
   }
   ```

5. **Test the installation**

   ```bash
   python scripts/run_tests.py --quick
   ```

## 📚 Usage

### Basic Job Search

```python
# In Claude Desktop, you can now use:
search_jobs_with_analysis_framework(
    query="python developer",
    location="London",
    max_results=15,
    include_analysis_framework=True
)
```

### Job Compatibility Analysis

```python
# Create personalized compatibility scoring
create_job_compatibility_template(
    user_skills=["Python", "Django", "PostgreSQL"],
    experience_years=5,
    salary_expectation=80000,
    remote_preference="hybrid"
)
```

### Application Tracking

```python
# Track job applications
track_job_application(
    job_url="https://example.com/job",
    company_name="TechCorp",
    position="Senior Developer",
    application_date="2024-01-15",
    status="applied"
)

# Get application status summary
get_application_status_summary()
```

### Career Planning

```python
# Create career progression roadmap
create_career_progression_framework(
    current_role="Software Developer",
    target_roles=["Senior Software Engineer", "Tech Lead"],
    current_skills=["Python", "JavaScript", "SQL"],
    timeline_months=24
)
```

## 🛠️ Available Tools

### Job Search Tools

- `search_jobs_with_analysis_framework` - Multi-source job search with analysis
- `create_job_compatibility_template` - Personalized job scoring framework
- `analyze_job_market_data` - Market trends and insights

### Application Management

- `track_job_application` - Track application status and follow-ups
- `get_application_status_summary` - Application pipeline overview
- `generate_application_templates` - CV, cover letter, and interview prep

### Career Development

- `create_career_progression_framework` - Personalized career roadmaps

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ADZUNA_APP_ID` | Adzuna API application ID | Yes |
| `ADZUNA_APP_KEY` | Adzuna API key | Yes |
| `DATABASE_PATH` | Custom database location | No |
| `ENABLE_EMAIL_ALERTS` | Enable email notifications | No |
| `SMTP_SERVER` | SMTP server for alerts | No |
| `EMAIL_USER` | Email username | No |
| `EMAIL_PASS` | Email password | No |
| `ALERT_EMAIL` | Alert recipient email | No |

### Optional Dependencies

```bash
# Data analysis capabilities
pip install ".[analysis]"

# Advanced web scraping
pip install ".[scraping]"

# System monitoring
pip install ".[monitoring]"

# Development tools
pip install ".[dev]"
```

## 📊 Monitoring

### Health Checks

Monitor system health with the built-in monitoring service:

```bash
# Check current status
python scripts/monitor.py status

# Start monitoring service
python scripts/monitor.py monitor

# Create database backup
python scripts/monitor.py backup

# Run maintenance tasks
python scripts/monitor.py maintenance
```

### Performance Metrics

The system tracks:

- API response times and success rates
- Database performance
- System resource usage
- Application pipeline metrics

## 🧪 Testing

### Run Tests

```bash
# Run all tests
python scripts/run_tests.py

# Quick smoke tests
python scripts/run_tests.py --quick

# Specific test categories
python scripts/run_tests.py --main
python scripts/run_tests.py --monitor

# Verbose output
python scripts/run_tests.py --verbose
```

### Test Coverage

- Unit tests for all core functionality
- Integration tests for complete workflows
- Performance tests for scalability
- Error handling and edge cases

## 📁 Project Structure

```bash
claude-job-agent/
├── src/claude_job_agent/
│   ├── main.py                 # Main MCP server and tools
│   ├── core/                   # Core functionality
│   ├── monitoring/             # Health checks and monitoring
│   ├── services/              # External service integrations
│   └── tools/                 # MCP tool implementations
├── scripts/
│   ├── monitor.py             # Monitoring CLI
│   └── run_tests.py           # Test runner
├── tests/
│   ├── test_main.py           # Main functionality tests
│   └── test_monitoring.py     # Monitoring system tests
├── data/                      # Database files
├── backups/                   # Database backups
├── logs/                      # Application logs
└── pyproject.toml            # Project configuration
```

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a virtual environment
3. Install development dependencies: `pip install -e ".[dev]"`
4. Run tests: `python scripts/run_tests.py`
5. Make your changes
6. Run tests again and ensure they pass
7. Submit a pull request

### Code Quality

- **Black** formatting: `black src/ tests/ scripts/`
- **Type hints** with mypy: `mypy src/`
- **Testing** with pytest: `pytest tests/`
- **Linting** with flake8: `flake8 src/`

## 📝 API Reference

### Job Search

The job search functionality provides structured data optimized for Claude's analysis:

```python
{
    "title": "Senior Python Developer",
    "company": "TechCorp Ltd",
    "location": "London",
    "salary_min": 70000,
    "salary_max": 90000,
    "extracted_features": {
        "tech_stack": ["python", "django", "postgresql"],
        "experience_level": "senior",
        "remote_policy": "hybrid",
        "has_benefits": true
    },
    "analysis_framework": {
        "analysis_prompts": {...},
        "scoring_criteria": {...}
    }
}
```

### Compatibility Scoring

Structured templates for consistent job evaluation:

```python
{
    "evaluation_criteria": {
        "technical_skills": {"weight": 40, "scoring_guide": {...}},
        "experience_level": {"weight": 25, "scoring_guide": {...}},
        "salary_alignment": {"weight": 20, "scoring_guide": {...}},
        "work_arrangement": {"weight": 15, "scoring_guide": {...}}
    },
    "output_format": {
        "compatibility_score": "Overall score 1-10",
        "recommendation": "High/Medium/Low priority",
        "application_tips": "Specific advice for this role"
    }
}
```

## 🚨 Troubleshooting

### Common Issues

**1. Database Permission Errors**

```bash
# Fix database permissions
chmod 664 data/jobs.db
chown user:group data/jobs.db
```

**2. API Rate Limiting**

```bash
# Check API usage in logs
tail -f logs/api_usage.log
```

**3. Claude Desktop Connection Issues**

```bash
# Validate MCP configuration
python -c "from src.claude_job_agent.main import mcp; print('MCP server loaded successfully')"
```

**4. Missing Dependencies**

```bash
# Install all dependencies
pip install -e ".[all]"
```

### Debug Mode

Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
python scripts/monitor.py status
```

## 📈 Performance

### Optimizations

- **Async Operations** - Non-blocking API calls
- **Database Indexing** - Optimized queries
- **Response Caching** - Reduced API calls
- **Batch Processing** - Efficient data handling

### Scalability

- Handles 1000+ job records efficiently
- Supports concurrent searches
- Automatic database cleanup
- Memory-efficient data structures

## 🔒 Security

### Data Protection

- Local database storage only
- No sensitive data in logs
- API credentials via environment variables
- Secure HTTP connections only

### Privacy

- No personal data shared with external services
- Local processing only
- User control over all data

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Anthropic** for Claude Desktop and MCP framework
- **Adzuna** for job search API
- **FastMCP** for simplified MCP server development
- **Community contributors** for testing and feedback

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/claude-job-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/claude-job-agent/discussions)
- **Documentation**: [Project Wiki](https://github.com/yourusername/claude-job-agent/wiki)

---

**Made with ❤️ for the Claude Desktop community**
